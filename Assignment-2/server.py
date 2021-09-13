import sys
import socket
import threading


# global hash table containing username-socket key-value pairs
# maintained by server to forward messages to corresponding users
socket_table = {}

def parse_data(data, delim=' '):
    fields = []
    temp = ""
    for i in range(0, len(data)):
        if data[i] == delim:
            fields.append(temp)
            temp = ""
        else:
            temp = temp + data[i]
    if temp != "":
        fields.append(temp)
    return fields

def broadcast(sock_frwd, forward_message, client_name, recp_name, responses):
    # forward message to "user"
    try:
        sock_frwd.sendall(forward_message.encode())
    except:
        # client probably closed socket
        print("Client Error: Client Socket closed.")
        # close corresponding socket, delete entry from table
        del socket_table[recp_name]
        sock_frwd.close()
        return
    # wait for reply from "user"
    try:
        reply = sock_frwd.recv(4096)
    except:
        # client probably closed socket
        print("Client Error: Client Socket closed.")
        # close corresponding socket, delete entry from table
        del socket_table[recp_name]
        sock_frwd.close()
        return
    # check for error
    if reply.decode() != "RECEIVED " + client_name + "\n\n":
        # there was some error, return false
        responses.append(False)
        return
    # no errors, return True
    responses.append(True)
    return

def client(sock_clnt, addr_clnt):
    
    # receive registration message from client
    try:
        registration_message = sock_clnt.recv(4096)
        fields = parse_data(registration_message.decode(), '\n')
    except:
        # client probably closed socket
        print("Client Error: Client Socket closed.")
        # close corresponding socket
        sock_clnt.close()
        return

    # check validity of message
    if len(fields) < 2 or len(fields) > 2 or fields[1] != "":
        # error in packet
        try:
            sock_clnt.sendall(("ERROR 101 No user registered\n\n").encode())
        except:
            # client probably closed socket
            print("Client Error: Client Socket closed.")
        # close socket
        sock_clnt.close()
        return

    # get words from parsed string
    fields = parse_data(fields[0])
    if len(fields) < 3 or len(fields) > 3 or fields[0] != "REGISTER" or (fields[1] != "TOSEND" and fields[1] != "TORECV"):
        # error in packet
        try:
            sock_clnt.sendall(("ERROR 101 No user registered\n\n").encode())
        except:
            # client probably closed socket
            print("Client Error: Client Socket closed.")
        # close socket
        sock_clnt.close()
        return

    # check username
    if not fields[2].isalnum():
        # invalid username, send error message
        try:
            sock_clnt.sendall(("ERROR 100 Malformed username\n\n").encode())
        except:
            # client probably closed socket
            print("Client Error: Client Socket closed.")
        # close socket
        sock_clnt.close()
        return

    # valid username, check if it is for sending or receiving
    if fields[1] == "TORECV":
        # add socket to table
        socket_table[fields[2]] = sock_clnt
        # send "successful" registration message back to client
        try:
            sock_clnt.sendall(("REGISTERED TORECV " + fields[2] + "\n\n").encode())
        except:
            # client probably closed socket
            print("Client Error: Client Socket closed.")
            del socket_table[fields[2]]
            sock_clnt.close()
        # close thread
        return
    
    # else, socket is for sending
    # send "successful" registration message back to client
    try:
        sock_clnt.sendall(("REGISTERED TOSEND " + fields[2] + "\n\n").encode())
    except:
        # client probably closed socket
        print("Client Error: Client Socket closed.")
        sock_clnt.close()
        if fields[2] in socket_table.keys():
            sock = socket_table[fields[2]]
            del socket_table[fields[2]]
            sock.close()
        return

    # store client name
    client_name = fields[2]

    # receive messages from this client
    while True:
        # wait for message from client
        try:
            incoming_message = sock_clnt.recv(4096)
            fields = parse_data(incoming_message.decode(), '\n')
        except:
            # client probably closed socket
            print("Client Error: Client Socket closed.")
            # close corresponding socket
            sock_clnt.close()
            if client_name in socket_table.keys():
                sock = socket_table[client_name]
                del socket_table[client_name]
                sock.close()
            return

        # check if header is complete
        if len(fields) < 4 or len(fields) > 4 or fields[2] != "":
            # error in packet
            try:
                sock_clnt.sendall(("ERROR 103 Header Incomplete\n\n").encode())
            except:
                # client probably closed socket
                print("Client Error: Client Socket closed.")
            # close sockets (sender and receiver)
            sock_clnt.close()
            if client_name in socket_table.keys():
                sock = socket_table[client_name]
                del socket_table[client_name]
                sock.close()
            # close thread
            return

        # parse all header lines of message   
        first_line = parse_data(fields[0])
        second_line = parse_data(fields[1])
        # store user message
        user_message = fields[3]
        
        # set error flag
        error = False

        # check first line
        if len(first_line) < 2 or len(first_line) > 2 or first_line[0] != "SEND":
            error = True
        else:
            recp_name = first_line[1]

        # check second line
        if len(second_line) < 2 or len(second_line) > 2:
            error = True
        else:
            if second_line[0] != "Content-length:" or not second_line[1].isdigit():
                error = True
            else:
                content_length = int(second_line[1])
                # check if the content length is correct or not
                if len(user_message.encode()) != content_length:
                    error = True

        # check for error
        if error:
            # send message to client
            try:
                sock_clnt.sendall(("ERROR 103 Header Incomplete\n\n").encode())
            except:
                # client probably closed socket
                print("Client Error: Client Socket closed.")
            # close sockets (sender and receiver)
            sock_clnt.close()
            if client_name in socket_table.keys():
                sock = socket_table[client_name]
                del socket_table[client_name]
                sock.close()
            # close thread
            return

        # no header errors, send message to recipient(s)
        forward_message = "FORWARD " + client_name + "\n" + second_line[0] + " " + str(content_length) + "\n\n" + user_message
        if recp_name in socket_table.keys():
            try:
                # forward message to recipient
                socket_table[recp_name].sendall(forward_message.encode())
                # wait for reply from recipient
                reply = socket_table[recp_name].recv(4096)
            except:
                # client probably closed socket
                print("Client Error: Client Socket closed.")
                sock = socket_table[recp_name]
                del socket_table[recp_name]
                sock.close()
                try:
                    sock_clnt.sendall(("ERROR 104 Unexpected\n\n").encode())
                except:
                    # client probably closed socket
                    print("Client Error: Client Socket closed.")
                    sock_clnt.close()
                    return
                continue

            # check for error
            if reply.decode() == "ERROR 103 Header Incomplete\n\n":
                # forward this reply to sender
                try:
                    sock_clnt.sendall(reply)
                except:
                    # client probably closed socket
                    print("Client Error: Client Socket closed.")
                # close sockets (sender and receiver)
                sock_clnt.close()
                if client_name in socket_table.keys():
                    sock = socket_table[client_name]
                    del socket_table[client_name]
                    sock.close()
                # close thread
                return
            elif reply.decode() == "RECEIVED " + client_name + "\n\n":
                # message delivered successfully, send SENT message to sender
                success_message = "SENT " + recp_name + "\n\n" 
                try:
                    sock_clnt.sendall(success_message.encode())
                except:
                    # client probably closed socket
                    print("Client Error: Client Socket closed.")
                    sock_clnt.close()
                    if client_name in socket_table.keys():
                        sock = socket_table[client_name]
                        del socket_table[client_name]
                        sock.close()
                    return
            else:
                # some other error, send error message
                try:
                    sock_clnt.sendall(("ERROR 104 Unexpected\n\n").encode())
                except:
                    # client probably closed socket
                    print("Client Error: Client Socket closed.")
                    sock_clnt.close()
                    if client_name in socket_table.keys():
                        sock = socket_table[client_name]
                        del socket_table[client_name]
                        sock.close()
                    return

        else:
            if recp_name == "ALL":
                # message is supposed to be broadcasted
                threads = []
                thread_count = 0
                responses = []
                for user in socket_table.keys():
                    if user == client_name:
                        # skip ownself
                        continue
                    try:
                        threads.append(threading.Thread(target=broadcast, args=(socket_table[user], forward_message, client_name, user, responses)))
                        threads[thread_count].start()
                        thread_count = thread_count + 1
                    except:
                        # error in broadcasting
                        responses.append(False)
                
                for thread in threads:
                    thread.join()
                
                error = False
                for response in responses:
                    if not response:
                        # some error in broadcasting
                        error = True
                        try:
                            sock_clnt.sendall(("ERROR 105 Broadcasting Error\n\n").encode())
                        except:
                            # client probably closed socket
                            print("Client Error: Client Socket closed.")
                            sock_clnt.close()
                            if client_name in socket_table.keys():
                                sock = socket_table[client_name]
                                del socket_table[client_name]
                                sock.close()
                            return
                        break
                if not error:
                    # successful broadcasting
                    try:
                        sock_clnt.sendall(("SENT ALL\n\n").encode())
                    except:
                        # client probably closed socket
                        print("Client Error: Client Socket closed.")
                        sock_clnt.close()
                        if client_name in socket_table.keys():
                            sock = socket_table[client_name]
                            del socket_table[client_name]
                            sock.close()
                        return
            else:
                # client does not exist, send error message back to sender
                try:
                    sock_clnt.sendall(("ERROR 102 Unable to send\n\n").encode())
                except:
                    # client probably closed socket
                    print("Client Error: Client Socket closed.")
                    sock_clnt.close()
                    if client_name in socket_table.keys():
                        sock = socket_table[client_name]
                        del socket_table[client_name]
                        sock.close()
                    return

def main():

    # create server side socket
    try:
        sock_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # reuse socket, do not wait for socket expiration (needed when rerunning server multiple times)
        sock_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # run process on port number 8000
        sock_server.bind(('', 8000))
    except:
        print("Error: Unable to create server-side socket. Program terminating!")
        return

    # initialize list of threads
    thread_client = []
    num_threads = 0

    # listen for client connections
    sock_server.listen(100)

    while True:
        # accept connection
        sock_clnt, addr_clnt = sock_server.accept()
        # create and start a new thread
        try:
            thread_client.append(threading.Thread(target=client, args=(sock_clnt, addr_clnt)))
            thread_client[num_threads].start()
            num_threads = num_threads + 1
        except:
            print("Client Error: There was an issue with multi-threading.")
            # close corresponding socket
            sock_clnt.close()
            continue


# run driver
main()


    