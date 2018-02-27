from xmlrpc.server import SimpleXMLRPCServer

def serve(addr, port):
    server = SimpleXMLRPCServer((addr, port))
    server.register_function(hello, 'hello')
    server.serve_forever()

# rpcのfunctoionが必要となる
def hello():
    return 'Hello, World.'

