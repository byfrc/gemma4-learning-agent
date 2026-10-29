"""Isolated API checks for Project Assistant; no live model or user data needed."""

import gc
import importlib
import json
from io import BytesIO
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from PIL import Image


class ProjectAssistantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="project-assistant-test-")
        root = Path(cls.tmp.name)
        cls.env = patch.dict(os.environ, {
            "CONVERSATION_DB_PATH": str(root / "history.db"),
            "KNOWLEDGE_DIR": str(root / "knowledge"),
            "RAG_INDEX_PATH": str(root / "rag.joblib"),
            "SUBJECT_BASE_DIR": str(root / "subjects"),
            "CHAT_LOG_PATH": str(root / "history.jsonl"),
            "FEEDBACK_LOG_PATH": str(root / "feedback.jsonl"),
            "AUTH_USERNAME": "teacher",
            "AUTH_PASSWORD": "test-password",
            "AUTH_SECRET_KEY": "isolated-project-assistant-test-key",
            "MODEL_PROVIDER": "mock",
            "DEFAULT_SUBJECT": "ai",
            "DOCUMENT_OCR_ENABLED": "off",
        })
        cls.env.start()
        cls.api = importlib.import_module("app.main")
        cls.client = TestClient(cls.api.app)
        cls.headers = {}
        for subject in ("ai", "java"):
            login = cls.client.post("/api/auth/login", json={
                "username": "teacher", "password": "test-password", "subject": subject,
            })
            login.raise_for_status()
            cls.headers[subject] = {"Authorization": "Bearer " + login.json()["access_token"]}
        for subject, filename, text in (
            ("ai", "cedar.md", "# Cedar project\nCedar's backend uses Rust and listens on port 47321. Its database is PostgreSQL."),
            ("ai", "platform.md", "# Project Assistant\nThe main components and request flow are the frontend app.js, the FastAPI backend, and SQLite storage. This is documentation of the hosting platform."),
            ("java", "maple.md", "# Maple project\nMaple's Java backend listens on port 48321. It uses H2 for storage."),
        ):
            response = cls.client.post(
                "/api/knowledge/upload", headers=cls.headers[subject],
                files={"file": (filename, text.encode(), "text/markdown")},
            )
            response.raise_for_status()

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.env.stop()
        # Existing SQLite context managers release their handles on collection.
        gc.collect()
        cls.tmp.cleanup()

    def create(self, subject="ai", mode="project_assistant"):
        response = self.client.post("/api/conversations", headers=self.headers[subject], json={
            "title": "Project test", "subject": subject, "agent_mode": mode,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["conversation_id"]

    def test_chat_retrieves_project_evidence_and_preserves_history_and_mode(self):
        conversation_id = self.create()
        generate = AsyncMock(return_value=("Cedar uses Rust and port 47321. Source: cedar.md.", "test-model"))
        with patch.object(self.api, "generate", generate):
            response = self.client.post("/api/chat", headers=self.headers["ai"], json={
                "conversation_id": conversation_id, "agent_mode": "project_assistant",
                "subject": "ai", "language": "en", "top_k": 2, "source_files": ["cedar.md"],
                "messages": [{"role": "user", "content": "Which backend and port does the Cedar project use?"}],
            })
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()["evidence"])
            self.assertEqual({row["source_file"] for row in response.json()["evidence"]}, {"cedar.md"})
            prompt = generate.await_args.kwargs["messages"][0]["content"]
            self.assertIn("Project Assistant", prompt)
            self.assertIn("47321", generate.await_args.kwargs["messages"][-1]["content"])
            self.assertIn("Answer only in English", prompt)
            self.assertNotIn("48321", prompt)
            self.assertNotIn("【当前项目部署事实】", prompt)

            followup = self.client.post("/api/chat", headers=self.headers["ai"], json={
                "conversation_id": conversation_id, "agent_mode": "project_assistant",
                "language": "en", "use_rag": False, "source_files": [],
                "messages": [{"role": "user", "content": "How can I check that port?"}],
            })
            self.assertEqual(followup.status_code, 200, followup.text)
            history = generate.await_args.kwargs["messages"]
            self.assertEqual([item["role"] for item in history], ["system", "user", "assistant", "user"])
            self.assertIn("47321", history[2]["content"])
            self.assertEqual(followup.json()["evidence"], [])

        detail = self.client.get(f"/api/conversations/{conversation_id}", headers=self.headers["ai"]).json()
        self.assertEqual(detail["agent_mode"], "project_assistant")
        self.assertEqual(len(detail["messages"]), 4)
        self.assertEqual(detail["messages"][1]["model_used"], "test-model")
        feedback = self.client.post(
            f"/api/messages/{detail['messages'][1]['message_id']}/feedback",
            headers=self.headers["ai"], json={"rating": 5, "feedback": "Useful explanation"},
        )
        self.assertEqual(feedback.status_code, 200, feedback.text)

    def test_java_subject_and_chinese_language(self):
        conversation_id = self.create("java")
        generate = AsyncMock(return_value=("Maple 使用 Java。", "test-model"))
        with patch.object(self.api, "generate", generate):
            response = self.client.post("/api/chat", headers=self.headers["java"], json={
                "conversation_id": conversation_id, "subject": "java",
                "agent_mode": "project_assistant", "language": "zh", "source_files": ["maple.md"],
                "messages": [{"role": "user", "content": "Maple backend port?"}],
            })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual({row["source_file"] for row in response.json()["evidence"]}, {"maple.md"})
        prompt = generate.await_args.kwargs["messages"][0]["content"]
        self.assertIn("只使用中文回答", prompt)
        self.assertNotIn("47321", prompt)

    def test_rename_accepts_new_mode_and_persists_it(self):
        conversation_id = self.create(mode="qa")
        response = self.client.patch(f"/api/conversations/{conversation_id}", headers=self.headers["ai"], json={
            "title": "My project", "agent_mode": "project_assistant",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["agent_mode"], "project_assistant")
        detail = self.client.get(f"/api/conversations/{conversation_id}", headers=self.headers["ai"]).json()
        self.assertEqual(detail["title"], "My project")
        self.assertEqual(detail["agent_mode"], "project_assistant")

    def test_invalid_mode_is_rejected_by_all_three_requests(self):
        conversation_id = self.create()
        requests = [
            ("POST", "/api/conversations", {"title": "Bad mode", "agent_mode": "invalid"}),
            ("PATCH", f"/api/conversations/{conversation_id}", {"title": "Bad mode", "agent_mode": "invalid"}),
            ("POST", "/api/chat", {"agent_mode": "invalid", "messages": [{"role": "user", "content": "Hi"}]}),
        ]
        for method, url, payload in requests:
            with self.subTest(url=url):
                response = self.client.request(method, url, headers=self.headers["ai"], json=payload)
                self.assertEqual(response.status_code, 422, response.text)

    def test_cross_subject_requests_are_rejected_before_generation(self):
        conversation_id = self.create("java")
        with patch.object(self.api, "generate", AsyncMock()) as generate:
            for payload in (
                {"subject": "java"}, {"conversation_id": conversation_id},
            ):
                response = self.client.post("/api/chat", headers=self.headers["ai"], json={
                    **payload, "agent_mode": "project_assistant",
                    "messages": [{"role": "user", "content": "Read this project"}],
                })
                self.assertEqual(response.status_code, 403, response.text)
            generate.assert_not_called()

    def test_existing_qa_keeps_its_tutor_context(self):
        generate = AsyncMock(return_value=("Tutor answer", "test-model"))
        with patch.object(self.api, "generate", generate):
            response = self.client.post("/api/chat", headers=self.headers["ai"], json={
                "agent_mode": "qa", "use_rag": False,
                "messages": [{"role": "user", "content": "Explain this Gemma deployment"}],
            })
        self.assertEqual(response.status_code, 200, response.text)
        prompt = generate.await_args.kwargs["messages"][0]["content"]
        self.assertIn("【当前项目部署事实】", prompt)
        self.assertNotIn("You are Project Assistant", prompt)

    def test_source_upload_preserves_indentation_and_is_available_to_chat(self):
        conversation_id = self.create()
        filename = "upload_probe.py"
        source = "def upload_probe(value):\n    return value + 17\n\nraise RuntimeError('SOURCE_FILES_ARE_NOT_EXECUTED')\n"
        uploaded_path = self.api.settings.knowledge_dir_for("ai") / filename
        try:
            response = self.client.post(f"/api/knowledge/upload?subject=ai&conversation_id={conversation_id}", headers=self.headers["ai"],
                files={"file": (filename, source.encode(), "text/plain")})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn(filename, response.json()["sources"])
            self.assertEqual(response.json()["source_files"], [filename])
            attachment = response.json()["attachment_message"]
            self.assertEqual(attachment["role"], "user")
            self.assertEqual(attachment["attachments"], [{"source_file": filename, "size_bytes": len(source.encode())}])
            detail = self.client.get(f"/api/conversations/{conversation_id}", headers=self.headers["ai"]).json()
            self.assertEqual(detail["source_files"], [filename])
            self.assertEqual(detail["messages"][0]["message_id"], attachment["message_id"])
            self.assertEqual(detail["messages"][0]["attachments"][0]["source_file"], filename)
            self.assertEqual(detail["messages"][0]["attachments"][0]["kind"], "file")
            generate = AsyncMock(return_value=("Your function adds 17.", "test-model"))
            with patch.object(self.api, "generate", generate):
                response = self.client.post("/api/chat", headers=self.headers["ai"], json={
                    "conversation_id": conversation_id,
                    "agent_mode": "project_assistant", "language": "en", "top_k": 0, "use_rag": False,
                    "messages": [{"role": "user", "content": "Using the uploaded project documentation, explain the main components and request flow. Cite the source filenames."}],
                })
            self.assertEqual(response.status_code, 200, response.text)
            rows = [row for row in response.json()["evidence"] if row["source_file"] == filename]
            self.assertTrue(rows)
            self.assertEqual({row["source_file"] for row in response.json()["evidence"]}, {filename})
            self.assertIn("\n    return value + 17", rows[0]["text"])
            prompt = generate.await_args.kwargs["messages"][0]["content"]
            self.assertIn("\n    return value + 17", generate.await_args.kwargs["messages"][-1]["content"])
            self.assertNotIn("app.js", prompt)
            self.client.put(f"/api/conversations/{conversation_id}/sources", headers=self.headers["ai"], json={"source_files": []}).raise_for_status()
            saved = self.client.get(f"/api/conversations/{conversation_id}", headers=self.headers["ai"]).json()
            self.assertEqual(len(saved["messages"]), 3)
            self.assertEqual(saved["messages"][0]["attachments"][0]["source_file"], filename)
            self.assertEqual(saved["messages"][1]["attachments"], [])
        finally:
            uploaded_path.unlink(missing_ok=True)
            self.api.rag_manager.rebuild("ai")

    def test_selected_files_persist_and_can_be_removed_without_affecting_other_chats(self):
        conversation_id = self.create()
        url = f"/api/conversations/{conversation_id}"
        response = self.client.put(url + "/sources", headers=self.headers["ai"], json={
            "source_files": ["cedar.md", "cedar.md"],
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["source_files"], ["cedar.md"])
        renamed = self.client.patch(url, headers=self.headers["ai"], json={"title": "Selected project"})
        self.assertEqual(renamed.json()["source_files"], ["cedar.md"])
        summaries = self.client.get("/api/conversations?subject=ai", headers=self.headers["ai"]).json()
        self.assertEqual(next(row for row in summaries if row["conversation_id"] == conversation_id)["source_files"], ["cedar.md"])
        other_id = self.create()
        self.assertEqual(self.client.get(f"/api/conversations/{other_id}", headers=self.headers["ai"]).json()["source_files"], [])
        removed = self.client.put(url + "/sources", headers=self.headers["ai"], json={"source_files": []})
        self.assertEqual(removed.json()["source_files"], [])
        self.assertTrue((self.api.settings.knowledge_dir_for("ai") / "cedar.md").exists())

    def test_missing_foreign_and_excess_sources_are_rejected_without_saving_a_message(self):
        conversation_id = self.create()
        url = f"/api/conversations/{conversation_id}"
        with patch.object(self.api, "generate", AsyncMock()) as generate:
            for files, status in ((["missing.java"], 400), (["maple.md"], 400), (["cedar.md"] * 13, 422)):
                with self.subTest(files=files):
                    selected = self.client.put(url + "/sources", headers=self.headers["ai"], json={"source_files": files})
                    self.assertEqual(selected.status_code, status, selected.text)
                    response = self.client.post("/api/chat", headers=self.headers["ai"], json={
                        "conversation_id": conversation_id, "agent_mode": "project_assistant", "source_files": files,
                        "messages": [{"role": "user", "content": "Explain the uploaded file"}],
                    })
                    self.assertEqual(response.status_code, status, response.text)
            generate.assert_not_called()
        self.assertEqual(self.client.get(url, headers=self.headers["ai"]).json()["messages"], [])
        foreign_id = self.create("java")
        response = self.client.put(f"/api/conversations/{foreign_id}/sources", headers=self.headers["ai"], json={"source_files": ["cedar.md"]})
        self.assertEqual(response.status_code, 403, response.text)
        response = self.client.post(f"/api/knowledge/upload?conversation_id={foreign_id}", headers=self.headers["ai"],
            files={"file": ("wrong-chat.md", b"Wrong conversation", "text/markdown")})
        self.assertEqual(response.status_code, 403, response.text)
        self.assertFalse((self.api.settings.knowledge_dir_for("ai") / "wrong-chat.md").exists())

    def test_project_without_selected_files_does_not_use_platform_evidence(self):
        generate = AsyncMock(return_value=("Please attach or choose a file.", "test-model"))
        with patch.object(self.api, "generate", generate):
            response = self.client.post("/api/chat", headers=self.headers["ai"], json={
                "agent_mode": "project_assistant", "use_rag": True, "top_k": 3,
                "messages": [{"role": "user", "content": "Explain the main components and request flow"}],
            })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["evidence"], [])
        prompt = generate.await_args.kwargs["messages"][0]["content"]
        self.assertIn("No files are selected", prompt)
        self.assertNotIn("app.js", prompt)

    def test_file_context_is_sent_with_current_question_after_old_answers(self):
        question = "Explain the main components and request flow."
        old_answer = "The project uses app.js, FastAPI, and SQLite."
        generate = AsyncMock(return_value=("Cedar uses Rust and PostgreSQL.", "test-model"))
        with patch.object(self.api, "generate", generate):
            response = self.client.post("/api/chat", headers=self.headers["ai"], json={
                "agent_mode": "project_assistant", "source_files": ["cedar.md"],
                "messages": [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": old_answer},
                    {"role": "user", "content": question},
                ],
            })
        self.assertEqual(response.status_code, 200, response.text)
        messages = generate.await_args.kwargs["messages"]
        self.assertEqual(messages[-2]["content"], old_answer)
        self.assertIn("cedar.md", messages[-1]["content"])
        self.assertIn("47321", messages[-1]["content"])
        self.assertTrue(messages[-1]["content"].endswith(question))
        self.assertNotIn("47321", messages[0]["content"])
        self.assertNotIn("app.js", messages[-1]["content"])

    def test_scoped_retrieval_includes_all_short_file_chunks_without_keyword_overlap(self):
        filename = "CompleteExample.java"
        source = "public class CompleteExample {\n" + "".join(
            f"    public int value{i}() {{ return {i}; }}\n" for i in range(30)
        ) + "}\n"
        uploaded_path = self.api.settings.knowledge_dir_for("ai") / filename
        try:
            uploaded = self.client.post("/api/knowledge/upload", headers=self.headers["ai"],
                files={"file": (filename, source.encode(), "text/plain")})
            self.assertEqual(uploaded.status_code, 200, uploaded.text)
            rag = self.api.rag_manager.get("ai")
            chunks = [row for row in rag.chunks if row["source_file"] == filename]
            self.assertGreater(len(chunks), 1)
            rows = rag.retrieve("zzzzzzzzzzzzzzzzzzzz", 1, source_files=[filename])
            self.assertEqual([row.text for row in rows], [row["text"] for row in chunks])
            self.assertEqual({row.source_file for row in rows}, {filename})
            self.assertTrue(all(row.score == 0 for row in rows))
            self.assertIn("value29", rows[-1].text)
            self.assertEqual(rag.retrieve("main components and request flow", 3, source_files=[]), [])
        finally:
            uploaded_path.unlink(missing_ok=True)
            self.api.rag_manager.rebuild("ai")

    def test_existing_database_migrates_without_losing_conversations_or_history(self):
        store = importlib.import_module("app.conversation_store")
        db_path = Path(self.tmp.name) / "legacy.db"
        # Build a populated database with the previous schema.
        store.init_db(db_path)
        conversation = store.create_conversation(db_path, "Existing project", "project_assistant", "ai", "teacher")
        conversation_id = conversation["conversation_id"]
        store.add_message(db_path, conversation_id, "user", "Keep my question", username="teacher")
        with sqlite3.connect(db_path) as conn:
            conn.execute("ALTER TABLE conversations DROP COLUMN source_files_json")
            conn.execute("ALTER TABLE messages DROP COLUMN attachments_json")
        conn.close()
        store.init_db(db_path)
        store.init_db(db_path)
        restored = store.get_conversation(db_path, conversation_id, username="teacher")
        self.assertEqual(restored["title"], "Existing project")
        self.assertEqual(restored["source_files"], [])
        self.assertEqual(store.get_messages(db_path, conversation_id)[0]["content"], "Keep my question")
        self.assertEqual(store.get_messages(db_path, conversation_id)[0]["attachments"], [])

    def test_upload_rejects_unsupported_empty_and_oversized_files(self):
        conversation_id = self.create()
        for filename, payload in (("blocked.exe", b"binary"), ("empty.md", b"")):
            with self.subTest(filename=filename):
                response = self.client.post(f"/api/knowledge/upload?conversation_id={conversation_id}", headers=self.headers["ai"],
                    files={"file": (filename, payload, "application/octet-stream")})
                self.assertEqual(response.status_code, 400, response.text)
                self.assertFalse((self.api.settings.knowledge_dir_for("ai") / filename).exists())
        self.assertEqual(self.client.get(f"/api/conversations/{conversation_id}", headers=self.headers["ai"]).json()["messages"], [])
        with patch.object(self.api.settings, "max_upload_mb", 1):
            response = self.client.post("/api/knowledge/upload", headers=self.headers["ai"],
                files={"file": ("too-big.md", b"a" * (1024 * 1024 + 1), "text/plain")})
            self.assertEqual(response.status_code, 400, response.text)

    @staticmethod
    def png_bytes():
        output = BytesIO()
        Image.new("RGB", (48, 32), "blue").save(output, format="PNG")
        return output.getvalue()

    def send_files(self, conversation_id, files, question="Use my question, source code, and image together.", subject="ai"):
        return self.client.post("/api/chat/attachments", headers=self.headers[subject], data={
            "payload": json.dumps({"conversation_id": conversation_id, "agent_mode": "project_assistant", "language": "en",
                "messages": [] if question is None else [{"role": "user", "content": question}]}),
        }, files=[("files", entry) for entry in files])

    def test_image_without_text_analyzes_only_the_new_image_and_supports_followup(self):
        conversation_id = self.create()
        generate = AsyncMock(return_value=("A blue image.", "test-model"))
        with patch.object(self.api, "generate", generate):
            earlier = self.client.post("/api/chat", headers=self.headers["ai"], json={
                "conversation_id": conversation_id, "agent_mode": "project_assistant",
                "source_files": ["cedar.md"], "language": "en",
                "messages": [{"role": "user", "content": "Explain the Cedar backend."}],
            })
            self.assertEqual(earlier.status_code, 200, earlier.text)
            response = self.send_files(conversation_id, [("picture.png", self.png_bytes(), "image/png")], question=None)
            self.assertEqual(response.status_code, 200, response.text)
            prompt = generate.await_args.kwargs["messages"]
            self.assertEqual(len(prompt), 2)
            self.assertIn("Analyze the attachments", prompt[-1]["content"])
            self.assertIn("picture.png", prompt[-1]["content"])
            self.assertEqual(len(prompt[-1]["images"]), 1)
            self.assertNotIn("cedar.md", str(prompt))
            self.assertEqual(response.json()["evidence"], [])
            self.assertEqual(response.json()["source_files"], ["cedar.md"])
            saved = self.client.get(f"/api/conversations/{conversation_id}", headers=self.headers["ai"]).json()
            user_message = saved["messages"][-2]
            self.assertEqual(user_message["content"], "")
            self.assertEqual(user_message["attachments"][0]["kind"], "image")
            self.assertEqual(response.json()["title"], "picture.png")
            followup = self.client.post("/api/chat", headers=self.headers["ai"], json={
                "conversation_id": conversation_id, "agent_mode": "project_assistant",
                "messages": [{"role": "user", "content": "What color was the image?"}],
            })
            self.assertEqual(followup.status_code, 200, followup.text)
            previous_images = [message for message in generate.await_args.kwargs["messages"][:-1] if message.get("images")]
            self.assertEqual(len(previous_images), 1)
            self.assertIn("picture.png", previous_images[0]["content"])

    def test_file_without_text_gets_content_analysis_without_inventing_user_text(self):
        filename = "automatic_probe.py"
        source = b"def cube(value):\n    return value ** 3\n"
        generate = AsyncMock(return_value=("This function cubes its input.", "test-model"))
        try:
            for question in (None, "", " \n\t "):
                with self.subTest(question=question), patch.object(self.api, "generate", generate):
                    conversation_id = self.create()
                    response = self.send_files(conversation_id, [(filename, source, "text/plain")], question=question)
                    self.assertEqual(response.status_code, 200, response.text)
                    prompt = generate.await_args.kwargs["messages"][-1]
                    self.assertIn("Analyze the attachments", prompt["content"])
                    self.assertIn("return value ** 3", prompt["content"])
                    self.assertEqual({item["source_file"] for item in response.json()["evidence"]}, {filename})
                    self.assertEqual(response.json()["user_message"]["content"], "")
                    self.assertEqual(response.json()["title"], filename)
        finally:
            (self.api.settings.knowledge_dir_for("ai") / filename).unlink(missing_ok=True)
            self.api.rag_manager.rebuild("ai")

    def test_empty_message_without_attachments_is_still_rejected(self):
        conversation_id = self.create()
        with patch.object(self.api, "generate", AsyncMock()) as generate:
            response = self.client.post("/api/chat", headers=self.headers["ai"], json={
                "conversation_id": conversation_id, "messages": [{"role": "user", "content": " \n "}],
            })
            self.assertEqual(response.status_code, 400, response.text)
            generate.assert_not_called()
        saved = self.client.get(f"/api/conversations/{conversation_id}", headers=self.headers["ai"]).json()
        self.assertEqual(saved["messages"], [])

    def test_text_code_and_image_are_one_message_and_reach_the_model_together(self):
        conversation_id = self.create()
        filename = "combined_probe.py"
        source = b"def combine(value):\n    return value * 3\n"
        generate = AsyncMock(return_value=("Combined answer.", "test-model"))
        try:
            with patch.object(self.api, "generate", generate):
                response = self.send_files(conversation_id, [(filename, source, "text/plain"), ("picture.png", self.png_bytes(), "image/png")])
            self.assertEqual(response.status_code, 200, response.text)
            prompt = generate.await_args.kwargs["messages"][-1]
            self.assertIn("Use my question, source code, and image together.", prompt["content"])
            self.assertIn("return value * 3", prompt["content"])
            self.assertEqual(len(prompt["images"]), 1)
            self.assertTrue(prompt["images"][0].startswith("/9j/"))
            self.assertEqual(response.json()["source_files"], [filename])
            saved = self.client.get(f"/api/conversations/{conversation_id}", headers=self.headers["ai"]).json()
            self.assertEqual(len(saved["messages"]), 2)
            message = saved["messages"][0]
            self.assertEqual(message["content"], "Use my question, source code, and image together.")
            self.assertEqual([item["kind"] for item in message["attachments"]], ["file", "image"])
            self.assertTrue(message["attachments"][1]["preview_data_url"].startswith("data:image/jpeg;base64,"))
            self.assertNotIn("images", message)
            with patch.object(self.api, "generate", generate):
                followup = self.client.post("/api/chat", headers=self.headers["ai"], json={
                    "conversation_id": conversation_id, "agent_mode": "project_assistant",
                    "messages": [{"role": "user", "content": "What color is the picture?"}],
                })
            self.assertEqual(followup.status_code, 200, followup.text)
            self.assertEqual(len(generate.await_args.kwargs["messages"][1]["images"]), 1)
        finally:
            (self.api.settings.knowledge_dir_for("ai") / filename).unlink(missing_ok=True)
            self.api.rag_manager.rebuild("ai")

    def test_invalid_image_rejects_the_whole_message_before_publishing_files(self):
        conversation_id = self.create()
        with patch.object(self.api, "generate", AsyncMock()) as generate:
            response = self.send_files(conversation_id, [
                ("not_published.md", b"Valid document", "text/plain"), ("bad.png", b"not an image", "image/png"),
            ])
            self.assertEqual(response.status_code, 400, response.text)
            generate.assert_not_called()
        self.assertFalse((self.api.settings.knowledge_dir_for("ai") / "not_published.md").exists())
        detail = self.client.get(f"/api/conversations/{conversation_id}", headers=self.headers["ai"]).json()
        self.assertEqual(detail["messages"], [])
        self.assertEqual(detail["source_files"], [])

    def test_model_failure_preserves_history_and_restores_overwritten_documents(self):
        conversation_id = self.create()
        original = (self.api.settings.knowledge_dir_for("ai") / "cedar.md").read_bytes()
        with patch.object(self.api, "generate", AsyncMock(side_effect=RuntimeError("Model unavailable"))):
            response = self.send_files(conversation_id, [("cedar.md", b"Temporary replacement", "text/plain"), ("picture.png", self.png_bytes(), "image/png")])
        self.assertEqual(response.status_code, 502, response.text)
        self.assertEqual((self.api.settings.knowledge_dir_for("ai") / "cedar.md").read_bytes(), original)
        detail = self.client.get(f"/api/conversations/{conversation_id}", headers=self.headers["ai"]).json()
        self.assertEqual(detail["messages"], [])
        self.assertEqual(detail["source_files"], [])
        self.assertEqual(list((self.api.settings.conversation_db_path.parent / "chat_images" / conversation_id).glob("*.bin")), [])

    def test_combined_messages_enforce_subject_access_and_image_limit(self):
        foreign_id = self.create("java")
        files = [("picture.png", self.png_bytes(), "image/png")]
        response = self.send_files(foreign_id, files)
        self.assertEqual(response.status_code, 403, response.text)
        conversation_id = self.create()
        response = self.send_files(conversation_id, files * 5)
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self.client.get(f"/api/conversations/{conversation_id}", headers=self.headers["ai"]).json()["messages"], [])

    def test_upload_preserves_admin_and_subject_permissions(self):
        registration = self.client.post("/api/auth/register", json={
            "username": "uploadstudent", "password": "student-password", "password_confirm": "student-password",
        })
        self.assertEqual(registration.status_code, 200, registration.text)
        login = self.client.post("/api/auth/login", json={
            "username": "uploadstudent", "password": "student-password", "subject": "ai",
        })
        self.assertEqual(login.status_code, 200, login.text)
        response = self.client.post("/api/knowledge/upload", headers={
            "Authorization": "Bearer " + login.json()["access_token"],
        }, files={"file": ("restricted.md", b"Student upload", "text/markdown")})
        self.assertEqual(response.status_code, 403, response.text)
        response = self.client.post("/api/knowledge/upload?subject=java", headers=self.headers["ai"],
            files={"file": ("restricted.md", b"Wrong subject", "text/markdown")})
        self.assertEqual(response.status_code, 403, response.text)


if __name__ == "__main__":
    unittest.main()
