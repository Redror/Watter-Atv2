import grpc
import chat_pb2
import chat_pb2_grpc
import threading
import random
import time
import sys
from concurrent import futures

DISCOVERY_SERVER_ADDRESS = 'localhost:50050'

# A classe Peer agora implementa o servicer PeerChatServicer
class Peer(chat_pb2_grpc.PeerChatServicer):
    def __init__(self, username, port):
        self.username = username
        self.port = port
        self.address = f'localhost:{self.port}'
        self.peers = {}

        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()
        print(f"Servidor do par {self.username} iniciado na porta {self.port}.")

        self._register_with_discovery_server()

        update_thread = threading.Thread(target=self._update_peers_list, daemon=True)
        update_thread.start()

    def _run_server(self):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        # Adicionamos o servicer correto (PeerChat) ao servidor do par
        chat_pb2_grpc.add_PeerChatServicer_to_server(self, server)
        server.add_insecure_port(self.address)
        server.start()
        server.wait_for_termination()

    def _register_with_discovery_server(self):
        try:
            with grpc.insecure_channel(DISCOVERY_SERVER_ADDRESS) as channel:
                # Usamos o DiscoveryStub para falar com o servidor
                stub = chat_pb2_grpc.DiscoveryStub(channel)
                peer_info = chat_pb2.PeerInfo(username=self.username, address=self.address)
                stub.Register(peer_info)
                print(f"Registrado com sucesso no servidor de descoberta.")
        except grpc.RpcError as e:
            print(f"Erro ao conectar ao servidor de descoberta: {e.status().details}", file=sys.stderr)
            sys.exit(1)

    def _update_peers_list(self):
        while True:
            try:
                with grpc.insecure_channel(DISCOVERY_SERVER_ADDRESS) as channel:
                    # Usamos o DiscoveryStub para falar com o servidor
                    stub = chat_pb2_grpc.DiscoveryStub(channel)
                    peer_list = stub.GetPeers(chat_pb2.Empty())
                    
                    current_peers = {}
                    for peer_info in peer_list.peers:
                        if peer_info.address != self.address:
                            current_peers[peer_info.username] = peer_info.address
                    
                    self.peers = current_peers

            except grpc.RpcError as e:
                print(f"Nao foi possivel atualizar a lista de pares: {e.status().details}", file=sys.stderr)
            
            time.sleep(10)

    # Este é o único método que o servidor do par precisa implementar
    def SendMessage(self, request, context):
        print(f"\n[{request.author_username}]: {request.content}")
        return chat_pb2.Empty()

    def start_chatting(self):
        print("\nDigite sua mensagem e pressione Enter para enviar a todos.")
        print("Pressione Ctrl+C para sair.")
        try:
            while True:
                content = input(f"[{self.username}]: ")
                if content:
                    message = chat_pb2.ChatMessage(author_username=self.username, content=content)
                    
                    peers_to_send = self.peers.copy()
                    
                    if not peers_to_send:
                        print("Nenhum outro par na rede para enviar mensagem.")
                        continue

                    for username, address in peers_to_send.items():
                        try:
                            with grpc.insecure_channel(address) as channel:
                                # Usamos o PeerChatStub para falar com outros pares
                                stub = chat_pb2_grpc.PeerChatStub(channel)
                                stub.SendMessage(message)
                        except grpc.RpcError:
                            print(f"Falha ao enviar mensagem para {username} @ {address}. O par pode estar offline.")
        except KeyboardInterrupt:
            print("\nSaindo do chat...")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python peer.py <username>")
        sys.exit(1)
        
    username = sys.argv[1]
    port = random.randint(50051, 50060) 
    
    peer = Peer(username, port)
    peer.start_chatting()