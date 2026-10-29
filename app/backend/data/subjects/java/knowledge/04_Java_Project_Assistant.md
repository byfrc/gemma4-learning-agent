# Java Project Assistant: debugging a small project

Project Assistant is available in the Java track. It uses documents and source files uploaded to the Java Knowledge Base, and code pasted into the conversation. Click Files beside the message box or drag a document or Java source file into the chat to upload it. Documents in the AI track are separate.

## Useful debugging context

Provide the exact compiler error or exception, the relevant method or a small complete example, the input, the expected result, and the actual result. For a build problem, include the Java version and the relevant Maven or Gradle configuration as text. Label each excerpt with its filename.

## Worked example: integer division by zero

Consider `int total = 12; int count = 0; int average = total / count;`. The code compiles, but integer division by zero raises `ArithmeticException` at runtime. A possible fix is to validate that count is positive before dividing. The correct behavior for an empty collection depends on the project requirements; it could be a helpful message or a defined empty result.

## Verifying a proposed fix

For the average example, check count equal to zero, count equal to one, and a normal positive count. Also decide whether fractional averages are required, since integer division truncates the result. These are suggested checks for the user to run; the chat agent does not execute them.

## Following up

After trying a suggested change, paste the new output or error in the same conversation. The agent receives the saved conversation history and can adjust its explanation. The separate Java Online IDE can run a small Main.java example, but Project Assistant does not invoke that IDE automatically.
