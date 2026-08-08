MATHEMAGIC ONLINE: THE SEQUEL
CIS 427 - Project 3

FILES
-----
server.py
client.py
logins.txt
README_SHORT.txt

The server automatically creates each user's solution history file when needed.


HOW TO RUN
----------
1. Open the project folder in VS Code.
2. Open a terminal and start the server:

   python server.py

3. Open another terminal and start a client:

   python client.py

4. Open more terminals and run client.py again to test multiple clients.

If "python" does not work on Windows, use "py" instead.


CONNECTING FROM ANOTHER COMPUTER
--------------------------------
On the server computer, run:

ipconfig

Find its IPv4 Address.

Then change this line in client.py:

SERVER_IP = "127.0.0.1"

to the server computer's IPv4 address.

Example:

SERVER_IP = "192.168.1.25"


LOGIN INFORMATION
-----------------
root  root22
john  john22
sally sally22
qiang qiang22


COMMANDS
--------
LOGIN username password

SOLVE -c radius
SOLVE -r side
SOLVE -r side1 side2

LIST
LIST -all

MESSAGE username message
MESSAGE -all message

LOGOUT
SHUTDOWN


EXAMPLES
--------
LOGIN john john22

SOLVE -c 4
Circle's circumference is 25.13 and area is 50.27

SOLVE -r 2
Rectangle's perimeter is 8.00 and area is 4.00

SOLVE -r 2 6
Rectangle's perimeter is 16.00 and area is 12.00

MESSAGE qiang Hello there!

LIST

LOGOUT


NOTES
-----
- You must LOGIN before using the other server commands.
- LIST shows the current user's saved solutions.
- LIST -all can only be used by root.
- MESSAGE sends a message to another logged-in user through the server.
- MESSAGE -all can only be used by root.
- LOGOUT closes only that client.
- SHUTDOWN stops the server.
- Multiple clients can be connected at the same time.
- Solution history is saved between logins.
- Invalid commands return 300 invalid command.
- Commands with an incorrect format return 301 message format error.