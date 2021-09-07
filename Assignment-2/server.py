import sys
import socket
import threading


# global hash table containing username-socket key-value pairs
# maintained by server to forward messages to corresponding users
socket_table = {}

def parse_reg_msg(reg_msg):
    fields = []
    temp = ""
    for i in range(0, len(reg_msg)):
        if reg_msg[i] == " " or reg_msg[i] == "\n" or reg_msg[i] == "\r":
            if temp != "":
                fields.append(temp)
                temp = ""
        else:
            temp = temp + reg_msg[i]
    if temp != "":
        fields.append(temp)
    return fields

def parse_packet(msg_packet):
    
    # parse the msg_packet received from server
    fields = []
    print(msg_packet + " " + str(len(msg_packet)))
    temp = ""
    for i in range(0, len(msg_packet)):
        print(temp)
        if msg_packet[i] == "\n":
            if temp != "":
                fields.append(temp)
                temp = ""
        else:
            temp = temp + msg_packet[i]
    if temp != "":
        fields.append(temp)
    print(fields)
    print("HowtoDJKks")
    # return parsed fields
    return fields

def client(sock_clnt, addr_clnt):
    
    # receive registration message from client
    reg_msg = sock_clnt.recv(4096)
    fields = parse_reg_msg(reg_msg.decode())
    print(fields)
    error = False

    # check validity of message
    if len(fields) < 3 or len(fields) > 3:
        # error in packet
        error = True
    else:
        if fields[0] != "REGISTER" or (fields[1] != "TOSEND" and fields[1] != "TORECV"):
            error = True
        else:
            # check username
            if not fields[2].isalnum():
                # invalid username, send error message
                sock_clnt.send(("ERROR 100 Malformed username\n\n").encode())
                # close thread
                return
            # valid username, check if it for sending or receiving
            if fields[1] == "TORECV":
                # add socket to table
                socket_table[fields[2]] = sock_clnt
                # send successful registration message back to client
                sock_clnt.send(("REGISTERED TORECV " + fields[2] + "\n\n").encode())
                # close thread
                return
            else:
                # socket for sending
                # send successful registration message back to client
                sock_clnt.send(("REGISTERED TOSEND " + fields[2] + "\n\n").encode())
                client_name = fields[2]
                print(client_name)
                # receive messages from this client
                while True:
                    # wait for message from client
                    incoming_message = sock_clnt.recv(4096)
                    if incoming_message == "":
                        continue
                    msg_packet = incoming_message.decode()
                    print(msg_packet)

                    # parse the packet to extract recipient name and message
                    recp_name = ""
                    message = ""
                    fields = parse_packet(msg_packet)
                    print(fields)
                    print("Hellow")
                    if len(fields) < 3 or len(fields) > 3:
                        # error with header
                        error = True
                    else:
                        if len(fields[0]) < 5 or fields[0][0:5] != "SEND ":
                            # error with header
                            error = True
                        else:
                            recp_name = fields[0][5:]
                            if recp_name == "":
                                # error with header
                                error = True
                        if len(fields[1]) < 16 or fields[1][0:16] != "Content-length: ":
                            # error with header
                            error = True
                        else:
                            temp = fields[1][16:]
                            if temp == "" or not temp.isdigit():
                                # error with header
                                error = True
                        message = fields[2]
                    
                    # check for errors
                    if error:
                        # send message to client
                        error_msg = "ERROR 103 Header Incomplete\n\n"
                        sock_clnt.send(error_msg.encode())
                        continue
                
                    # no header errors, send message to recipient(s)
                    forward_message = "FORWARDED " + client_name + "\n" + fields[1] + "\n\n" + message
                    if recp_name in socket_table.keys():
                        # forward message to recipient
                        socket_table[recp_name].send(forward_message.encode())
                        # wait for reply from recipient
                        reply = socket_table[recp_name].recv(4096)

                        # check for error
                        if reply.decode() == "ERROR 103 Header Incomplete\n\n":
                            # forward this message to sender
                            sock_clnt.send(reply)
                        else:
                            # message delivered successfully, send SENT message to sender
                            success = "SENT " + recp_name + "\n\n" 
                            sock_clnt.send(success.encode())                        
                    else:
                        # client does not exist, send error message back to sender
                        sock_clnt.send(("ERROR 102 Unable to send\n\n").encode())
                    

    # check for error
    if error:
        # return ERROR 101
        sock_clnt.send(("ERROR 101 No user registered\n\n").encode())
        # close thread
        return

def main():

    # create server side socket
    try:
        sock_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # run process on port number 5000
        sock_server.bind(('', 8000))
    except:
        print("Error: Unable to create server-side socket. Program terminating!")
        sys.exit()

    # initialize thread of lists
    thread_client = []
    num_threads = 0

    # listen for client connections
    try:
        sock_server.listen(5)
    except:
        print("Error: Unable to listen to arriving connections. Server closing down!")
        sock_server.close()
        sys.exit()

    while True:
        # accept connection
        sock_clnt, addr_clnt = sock_server.accept()
        print("New connection")
        # create and start a new thread
        try:
            thread_client.append(threading.Thread(target=client, args=(sock_clnt, addr_clnt)))
            thread_client[num_threads].start()
            num_threads = num_threads + 1
        except:
            print("Error: There was an issue with multi-threading. Server closing down!")
            sys.exit()

main()


    