"""Visual Studio entry point."""
from backend.app import create_app
from waitress import serve

if __name__=='__main__':
    serve(create_app(),host='127.0.0.1',port=5000,threads=8)
