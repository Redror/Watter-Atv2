import grpc
import chat_pb2
import chat_pb2_grpc
import threading
import random
import time
import sys

# Endereço do servidor de descoberta
DISCOVERY_SERVER_ADDRESS = 'localhost:50050'

class Peer:
    def __init__(self, username, port):
        self.username = username
        self.port = port
        self.address = f'localhost:{self.port}'
        self.peers = {} # Dicionário para armazenar stubs de outros pares: {'username': stub}

        # Inicia o servidor do próprio par em uma thread separada para escutar mensagens
        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()
        print(f"✅ Servidor do par {self.username} iniciado na porta {self.port}.")

        # Registra-se no servidor de descoberta
        self._register_with_discovery_server()

        # Inicia a thread que periodicamente atualiza a lista de pares
        update_thread = threading.Thread(target=self._update_peers_list, daemon=True)
        update_thread.start()

    def _run_server(self):
        """Inicia o servidor gRPC do próprio par para receber mensagens."""
        server = grpc.server(threading.BoundedThreadPool(max_workers=10))
        chat_pb2_grpc.add_ChatServicer_to_server(self, server)
        server.add_insecure_port(self.address)
        server.start()
        server.wait_for_termination()

    def _register_with_discovery_server(self):
        """Conecta-se ao servidor de descoberta e se registra."""
        try:
            with grpc.insecure_channel(DISCOVERY_SERVER_ADDRESS) as channel:
                stub = chat_pb2_grpc.ChatStub(channel)
                peer_info = chat_pb2.PeerInfo(username=self.username, address=self.address)
                stub.Register(peer_info)
                print(f"Registrado com sucesso no servidor de descoberta.")
        except grpc.RpcError as e:
            print(f"Erro ao conectar ao servidor de descoberta: {e.status().details}", file=sys.stderr)
            sys.exit(1)


    def _update_peers_list(self):
        """Periodicamente busca a lista de pares do servidor de descoberta."""
        while True:
            try:
                with grpc.insecure_channel(DISCOVERY_SERVER_ADDRESS) as channel:
                    stub = chat_pb2_grpc.ChatStub(channel)
                    peer_list = stub.GetPeers(chat_pb2.Empty())
                    
                    current_peers = {}
                    for peer_info in peer_list.peers:
                        if peer_info.address != self.address: # Não se conectar a si mesmo
                            current_peers[peer_info.username] = peer_info.address
                    
                    # Simples atualização da lista de pares conhecidos
                    self.peers = current_peers

            except grpc.RpcError as e:
                print(f"Não foi possível atualizar a lista de pares: {e.status().details}", file=sys.stderr)
            
            time.sleep(10) # Atualiza a lista a cada 10 segundos


    # --- Implementação do serviço gRPC (para atuar como servidor) ---
    def SendMessage(self, request, context):
        """Método chamado por outros pares para me enviar uma mensagem."""
        print(f"\n [{request.author_username}]: {request.content}")
        return chat_pb2.Empty()


    # --- Lógica de cliente (para enviar mensagens) ---
    def start_chatting(self):
        """Loop principal para enviar mensagens para todos os outros pares."""
        print("\nDigite sua mensagem e pressione Enter para enviar a todos.")
        print("Pressione Ctrl+C para sair.")
        try:
            while True:
                content = input(f"[{self.username}]: ")
                if content:
                    message = chat_pb2.ChatMessage(author_username=self.username, content=content)
                    
                    # Itera sobre uma cópia para evitar problemas de concorrência com a thread de atualização
                    peers_to_send = self.peers.copy()
                    
                    if not peers_to_send:
                        print("Nenhum outro par na rede para enviar mensagem.")
                        continue

                    for username, address in peers_to_send.items():
                        try:
                            with grpc.insecure_channel(address) as channel:
                                stub = chat_pb2_grpc.ChatStub(channel)
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
    # Usar uma porta aleatória para evitar conflitos ao rodar múltiplos pares na mesma máquina
    port = random.randint(50051, 50060) 
    
    peer = Peer(username, port)
    peer.start_chatting()