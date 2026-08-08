import math
import os
import socket
import threading

# Server configuration
HOST = "0.0.0.0"
SERVER_PORT = 4270
LOGIN_FILE = "logins.txt"

# Tracks which logged-in username belongs to which connected socket.
active_users = {}

# Locks protect shared data when multiple client threads run at once.
active_lock = threading.Lock()
file_lock = threading.Lock()
server_socket = None
server_running = True


def load_users():
    # Read allowed usernames and passwords from logins.txt.
    users = {}
    with open(LOGIN_FILE, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.split()
            if len(parts) == 2:
                users[parts[0]] = parts[1]
    return users


USERS = load_users()


def send(sock, message):
    # Send one newline-terminated message to a client.
    try:
        sock.sendall((message + "\n").encode("utf-8"))
        return True
    except OSError:
        return False


def clean_number(value):
    # Display whole numbers without an unnecessary .0.
    return str(int(value)) if float(value).is_integer() else str(value)


def history_file(username):
    # Return the filename used to store one user's SOLVE history.
    return f"{username}_solutions.txt"


def save_history(username, text):
    # Append one SOLVE result or error to the user's history file.
    with file_lock:
        with open(history_file(username), "a", encoding="utf-8") as file:
            file.write(text + "\n")


def read_history(username):
    # Read all saved SOLVE entries for one user.
    filename = history_file(username)
    if not os.path.exists(filename):
        return []

    with file_lock:
        with open(filename, "r", encoding="utf-8") as file:
            return [line.rstrip() for line in file if line.strip()]


def solve(parts):
    # Process SOLVE commands for circles and rectangles.
    if len(parts) < 2:
        return "301 message format error", None

    flag = parts[1]

    # Circle format: SOLVE -c radius
    if flag == "-c":
        if len(parts) == 2:
            return "Error:  No radius found", "Error:  No radius found"
        if len(parts) != 3:
            return "301 message format error", None

        try:
            radius = float(parts[2])
            if radius < 0:
                raise ValueError
        except ValueError:
            return "Error:  Invalid radius", "Error:  Invalid radius"

        circumference = 2 * math.pi * radius
        area = math.pi * radius ** 2
        response = (
            f"Circle's circumference is {circumference:.2f} "
            f"and area is {area:.2f}"
        )
        history = f"radius {clean_number(radius)}:  {response}"
        return response, history

    # Rectangle format: SOLVE -r side OR SOLVE -r side1 side2
    if flag == "-r":
        if len(parts) == 2:
            return "Error:  No sides found", "Error:  No sides found"
        if len(parts) not in (3, 4):
            return "301 message format error", None

        try:
            side1 = float(parts[2])
            side2 = float(parts[3]) if len(parts) == 4 else side1
            if side1 < 0 or side2 < 0:
                raise ValueError
        except ValueError:
            return "Error:  Invalid side", "Error:  Invalid side"

        perimeter = 2 * (side1 + side2)
        area = side1 * side2
        response = (
            f"Rectangle's perimeter is {perimeter:.2f} "
            f"and area is {area:.2f}"
        )

        sides = clean_number(side1)
        if len(parts) == 4:
            sides += f" {clean_number(side2)}"

        return response, f"sides {sides}:  {response}"

    return "301 message format error", None


def send_list(sock, usernames):
    # Send saved solution history for one or more users.
    for username in usernames:
        send(sock, username)
        entries = read_history(username)

        if entries:
            for entry in entries:
                send(sock, f"    {entry}")
        else:
            send(sock, "    No interactions yet")

    send(sock, "END_LIST")


def remove_user(username, sock):
    # Remove a user from the active-user table when they disconnect.
    if username is None:
        return

    with active_lock:
        if active_users.get(username) is sock:
            del active_users[username]


def handle_message(sock, sender, command_line):
    # Route MESSAGE commands through the server to connected clients.
    parts = command_line.split(maxsplit=2)

    if len(parts) != 3 or not parts[2].strip():
        send(sock, "301 message format error")
        return

    recipient, text = parts[1], parts[2].strip()

    print("Message from client:")
    print(text)

    # Only root may broadcast a message to all logged-in users.
    if recipient == "-all":
        if sender != "root":
            send(sock, "Error:  you are not the root user")
            return

        with active_lock:
            recipients = list(active_users.items())

        delivered = 0
        for username, client in recipients:
            if username != sender and send(client, f"Message from {sender}:"):
                send(client, text)
                delivered += 1

        print("Sending to all logged-in users")
        send(sock, "200 OK" if delivered else "No other users are logged in")
        return

    if recipient not in USERS:
        print(f"User {recipient} doesn't exist. Informing client.")
        send(sock, f"User {recipient} does not exist")
        return

    with active_lock:
        recipient_socket = active_users.get(recipient)

    if recipient_socket is None:
        print(f"{recipient} is not logged in. Informing client.")
        send(sock, f"User {recipient} is not logged in")
        return

    print(f"Sending to {recipient}")

    if send(recipient_socket, f"Message from {sender}:"):
        send(recipient_socket, text)
        send(sock, "200 OK")
    else:
        remove_user(recipient, recipient_socket)
        send(sock, f"User {recipient} is not logged in")


def stop_server(requesting_socket):
    # Confirm shutdown, close client sockets, and stop the server.
    global server_running

    send(requesting_socket, "200 OK")
    server_running = False

    with active_lock:
        clients = list(active_users.values())
        active_users.clear()

    for client in clients:
        if client is not requesting_socket:
            send(client, "SERVER_SHUTDOWN")
        try:
            client.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            client.close()
        except OSError:
            pass

    try:
        server_socket.close()
    except OSError:
        pass


def handle_client(sock, address):
    # Handle one client connection in its own thread.
    username = None
    buffer = ""

    print(f"Client connected: {address}")

    try:
        while server_running:
            data = sock.recv(4096)
            if not data:
                break

            buffer += data.decode("utf-8")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                print(f"Received from {address}: {line}")
                parts = line.split()
                command = parts[0].upper()

                # Clients must LOGIN successfully before using other commands.
                if username is None:
                    if command != "LOGIN":
                        send(sock, "FAILURE: Please login before using server commands.")
                        continue

                    if len(parts) != 3:
                        send(sock, "301 message format error")
                        continue

                    user, password = parts[1], parts[2]

                    if USERS.get(user) != password:
                        send(
                            sock,
                            "FAILURE: Please provide correct username and password. Try again."
                        )
                        continue

                    with active_lock:
                        if user in active_users:
                            send(sock, "FAILURE: User is already logged in.")
                            continue
                        active_users[user] = sock

                    username = user
                    send(sock, "SUCCESS")
                    continue

                # Handle commands after login.
                if command == "LOGIN":
                    send(sock, "FAILURE: User is already logged in.")

                elif command == "SOLVE":
                    # Calculate geometry and save the result.
                    response, history = solve(parts)
                    send(sock, response)
                    if history:
                        save_history(username, history)

                elif command == "LIST":
                    # LIST is personal; LIST -all is restricted to root.
                    if len(parts) == 1:
                        send_list(sock, [username])
                    elif len(parts) == 2 and parts[1] == "-all":
                        if username == "root":
                            send_list(sock, USERS.keys())
                        else:
                            send(sock, "Error:  you are not the root user")
                    else:
                        send(sock, "301 message format error")

                elif command == "MESSAGE":
                    # Send a private message or root broadcast.
                    handle_message(sock, username, line)

                elif command == "LOGOUT":
                    # LOGOUT closes only this client.
                    if len(parts) != 1:
                        send(sock, "301 message format error")
                    else:
                        send(sock, "200 OK")
                        return

                elif command == "SHUTDOWN":
                    # SHUTDOWN stops the complete server.
                    if len(parts) != 1:
                        send(sock, "301 message format error")
                    else:
                        stop_server(sock)
                        return

                else:
                    send(sock, "300 invalid command")

    except (ConnectionResetError, ConnectionAbortedError, OSError):
        pass

    finally:
        remove_user(username, sock)
        try:
            sock.close()
        except OSError:
            pass
        print(f"Client disconnected: {address}")


def main():
    # Create the TCP server socket and continuously accept clients.
    global server_socket

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, SERVER_PORT))
    server_socket.listen()

    print("MatheMagic Online server is running.")
    print(f"Listening on port {SERVER_PORT}")

    try:
        while server_running:
            try:
                client, address = server_socket.accept()
            except OSError:
                break

            # Each client gets its own thread so clients can work simultaneously.
            threading.Thread(
                target=handle_client,
                args=(client, address),
                daemon=True
            ).start()

    except KeyboardInterrupt:
        print("\nServer stopped manually.")

    finally:
        try:
            server_socket.close()
        except OSError:
            pass
        print("Server terminated.")


if __name__ == "__main__":
    main()