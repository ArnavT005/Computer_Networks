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
            if temp != "":
                fields.append(temp)
                temp = ""
        else:
            temp = temp + data[i]
    if temp != "":
        fields.append(temp)
    return fields

def client(sock_clnt, addr_clnt):
    
    # receive registration message from client
    registration_message = sock_clnt.recv(4096)
    fields = parse_data(registration_message.decode(), '\n')

    # check validity of message
    if len(fields) < 1 or len(fields) > 1:
        # error in packet
        sock_clnt.send(("ERROR 101 No user registered\n\n").encode())
        return

    # get words from parsed string
    fields = parse_data(fields[0])
    if len(fields) < 3 or len(fields) > 3:
        # error in packet
        sock_clnt.send(("ERROR 101 No user registered\n\n").encode())
        return

    # check if it is a send or a receive message
    if fields[0] != "REGISTER" or (fields[1] != "TOSEND" and fields[1] != "TORECV"):
        # error in packet
        sock_clnt.send(("ERROR 101 No user registered\n\n").encode())
        return

    # check username
    if not fields[2].isalnum():
        # invalid username, send error message
        sock_clnt.send(("ERROR 100 Malformed username\n\n").encode())
        # close thread
        return

    # valid username, check if it is for sending or receiving
    if fields[1] == "TORECV":
        # add socket to table
        socket_table[fields[2]] = sock_clnt
        # send "successful" registration message back to client
        sock_clnt.send(("REGISTERED TORECV " + fields[2] + "\n\n").encode())
        # close thread
        return
    
    # else, socket is for sending
    # send "successful" registration message back to client
    sock_clnt.send(("REGISTERED TOSEND " + fields[2] + "\n\n").encode())
    # store client name
    client_name = fields[2]

    # receive messages from this client
    while True:
        # wait for message from client
        incoming_message = sock_clnt.recv(4096)
        fields = parse_data(incoming_message.decode(), '\n')

        # check if header is complete
        if len(fields) < 3 or len(fields) > 3:
            # error in packet
            sock_clnt.send(("ERROR 103 Header Incomplete\n\n").encode())
            continue

        # parse all header lines of message   
        first_line = parse_data(fields[0])
        second_line = parse_data(fields[1])
        # store user message
        user_message = fields[2]
        
        # set error flag
        error = False

        # check first line
        if len(first_line) < 2 or len(first_line) > 2:
            error = True
        else:
            if first_line[0] != "SEND":
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
            sock_clnt.send(("ERROR 103 Header Incomplete\n\n").encode())
            continue

        # no header errors, send message to recipient(s)
        forward_message = "FORWARD " + client_name + "\n" + second_line[0] + " " + str(content_length) + "\n\n" + user_message
        if recp_name in socket_table.keys():
            # forward message to recipient
            socket_table[recp_name].send(forward_message.encode())
            # wait for reply from recipient
            reply = socket_table[recp_name].recv(4096)
            # check for error
            if reply.decode() == "ERROR 103 Header Incomplete\n\n":
                # forward this reply to sender
                sock_clnt.send(reply)
            elif reply.decode() == "RECEIVED " + client_name + "\n\n":
                # message delivered successfully, send SENT message to sender
                success_message = "SENT " + recp_name + "\n\n" 
                sock_clnt.send(success_message.encode())    
            else:
                # some other error, send error message
                sock_clnt.send(("ERROR 103 Header Incomplete\n\n").encode())               
        else:
            # client does not exist, send error message back to sender
            sock_clnt.send(("ERROR 102 Unable to send\n\n").encode())

    return

def main():

    # create server side socket
    try:
        sock_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # run process on port number 8000
        sock_server.bind(('', 8000))
    except:
        print("Error: Unable to create server-side socket. Program terminating!")
        sys.exit()

    # initialize thread of lists
    thread_client = []
    num_threads = 0

    # listen for client connections
    sock_server.listen(5)

    while True:
        # accept connection
        sock_clnt, addr_clnt = sock_server.accept()
        # create and start a new thread
        try:
            thread_client.append(threading.Thread(target=client, args=(sock_clnt, addr_clnt)))
            thread_client[num_threads].start()
            num_threads = num_threads + 1
        except:
            print("Error: There was an issue with multi-threading. Server closing down!")
            # close all opened sockets
            sock_clnt.close()
            for sock in socket_table.values():
                sock.close()
            sock_server.close()
            sys.exit()

main()


    