"""
Serveur HTTP simple pour servir l'interface web AFTT Data Explorer
"""
import http.server
import socketserver
import os
import sys
import json
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

PORT = 8080

class AFTTHandler(http.server.SimpleHTTPRequestHandler):
    """Handler personnalisé pour servir les fichiers statiques et JSON"""
    
    def __init__(self, *args, **kwargs):
        # Le dossier web contient les fichiers statiques
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)
    
    def end_headers(self):
        # CORS headers pour permettre le chargement local
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_GET(self):
        # API pour charger les données depuis le dossier data
        if self.path == '/api/clubs':
            self.serve_json('../data/clubs.json')
        elif self.path.startswith('/api/members/'):
            club_code = self.path.split('/')[-1]
            self.serve_json(f'../data/members_{club_code}.json')
        elif self.path.startswith('/api/player/'):
            licence = self.path.split('/')[-1]
            self.serve_json(f'../data/player_{licence}.json')
        elif self.path == '/api/list':
            self.list_data_files()
        else:
            super().do_GET()
    
    def serve_json(self, filepath):
        """Sert un fichier JSON"""
        base_path = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_path, filepath)
        
        if os.path.exists(full_path):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            with open(full_path, 'r', encoding='utf-8') as f:
                self.wfile.write(f.read().encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'File not found'}).encode('utf-8'))
    
    def list_data_files(self):
        """Liste les fichiers de données disponibles"""
        base_path = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(base_path, '../data')
        
        files = {
            'clubs': None,
            'members': [],
            'players': []
        }
        
        if os.path.exists(data_path):
            for filename in os.listdir(data_path):
                if filename == 'clubs.json':
                    files['clubs'] = filename
                elif filename.startswith('members_') and filename.endswith('.json'):
                    club_code = filename.replace('members_', '').replace('.json', '')
                    files['members'].append(club_code)
                elif filename.startswith('player_') and filename.endswith('.json'):
                    licence = filename.replace('player_', '').replace('.json', '')
                    files['players'].append(licence)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(files).encode('utf-8'))

def run_server():
    """Lance le serveur HTTP"""
    with socketserver.TCPServer(("", PORT), AFTTHandler) as httpd:
        print(f"🏓 AFTT Data Explorer")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📡 Serveur démarré sur http://localhost:{PORT}")
        print(f"📁 Dossier web: {os.path.dirname(os.path.abspath(__file__))}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"Appuyez sur Ctrl+C pour arrêter")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Serveur arrêté")
            sys.exit(0)

if __name__ == "__main__":
    run_server()
