import grpc
import chat_pb2
import chat_pb2_grpc
from concurrent import futures
import time
import threading

class ChatServicer(chat_pb2_grpc.ChatServicer):
    def __init__(self):
        self.peers = []
        self.lock = threading.Lock()
        print("Servidor de Descoberta iniciado.")

    def Register(self, request, context):
        """
        Registra um novo par na lista de pares conhecidos.
        """
        with self.lock:
            # Evita adicionar pares duplicados (mesmo usuário e endereço)
            if not any(p.username == request.username and p.address == request.address for p in self.peers):
                print(f"Registrando novo par: {request.username} @ {request.address}")
                self.peers.append(request)
        return chat_pb2.Empty()

    def GetPeers(self, request, context):
        """
        Retorna a lista de todos os pares registrados.
        """
        with self.lock:
            print(f"Enviando lista de {len(self.peers)} pares.")
            peer_list = chat_pb2.PeerList(peers=self.peers)
            return peer_list

def serve():
    """
    Configura e inicia o servidor gRPC.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServicer_to_server(ChatServicer(), server)
    server.add_insecure_port('[::]:50050') # Servidor de descoberta escuta na porta 50050
    server.start()
    print("Servidor de Descoberta escutando na porta 50050.")
    try:
        while True:
            time.sleep(86400) # Mantém o servidor rodando por um dia
    except KeyboardInterrupt:
        print("Desligando o servidor.")
        server.stop(0)

if __name__ == '__main__':
    serve()