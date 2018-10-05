import socket

HOST = '192.168.0.10'
PORT = 7
number_of_packets = 1000

def tcp_client():
    global number_of_packets
    client = socket.socket( socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(30)
    client.connect(( HOST, PORT ))
    client.settimeout(None)
    print ("connected!")
    msg = "TCP_ECHO_DEMO"
    i = 0
    while True:#i != number_of_packets):
        client.send(msg+str(i+1))
        response = client.recv(8192)
        print(response)
        i += 1
    client.close()


def tcp_client_1():
    global number_of_packets, client
    print("-------------- TCP CLIENT ---------------")
    clnt_flag = True
    attempts = 0
    while clnt_flag:
        
        try:
            attempts +=1
            if attempts > 1000:
                break
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(600)
            client.connect((HOST, PORT))
            client.settimeout(None)
            print("----------------------------------------")
            print ("TCP_ECHO_CLIENT CONNECTED!")
            msg = "TCP_ECHO_DEMO_"
            i = 0
            while i != number_of_packets:
                client.send(msg+str(i+1))
                response = client.recv(8192)
                #print(response)
                i += 1
            client.close()
            print("TCP_ECHO_CLIENT FINISHED!")
            print("----------------------------------------")

        except Exception as msg:
            print(" [%i] ERROR: %s, reconnecting" %(attempts, msg))
    return

if __name__ == '__main__':
      tcp_client_1()
