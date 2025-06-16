import grpc
import chat_pb2
import chat_pb2_grpc
from concurrent import futures
import time
import threading

# O Servicer agora implementa o serviço Discovery
class DiscoveryServicer(chat_pb2_grpc.DiscoveryServicer):
    def __init__(self):
        self.peers = []
        self.lock = threading.Lock()
        print("Servidor de Descoberta iniciado.")

    def Register(self, request, context):
        with self.lock:
            if not any(p.username == request.username and p.address == request.address for p in self.peers):
                print(f"Registrando novo par: {request.username} @ {request.address}")
                self.peers.append(request)
        return chat_pb2.Empty()

    def GetPeers(self, request, context):
        with self.lock:
            print(f"Enviando lista de {len(self.peers)} pares.")
            peer_list = chat_pb2.PeerList(peers=self.peers)
            return peer_list

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    # Adicionamos o servicer correto ao servidor
    chat_pb2_grpc.add_DiscoveryServicer_to_server(DiscoveryServicer(), server)
    server.add_insecure_port('[::]:50050')
    server.start()
    print("Servidor de Descoberta escutando na porta 50050.")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        print("Desligando o servidor.")
        server.stop(0)

if __name__ == '__main__':
    serve()