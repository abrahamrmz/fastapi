from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()
active_sessions = []

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-EVSTQN3/azprG1Anm3QDgpJLIm9Nao0Yz1ztcQTwFspd3yD65VohhpuuCOmLASjC" crossorigin="anonymous">
    </head>
    <body>
        <div class="container">
            <h1>Chat 3000 by Abraham R.</h1>
            <div class="col-6">
                <div class="input-group mb-3">
                    <input type="text" class="form-control" id="nickname" placeholder="Ingresa tu apodo">
                    <div class="input-group-append">
                        <button class="btn btn-outline-secondary" id="connectButton" onclick="connectWebSocket()">Conectar</button>
                    </div>
                </div>
                <div id="errorMessage" style="display: none;">
                    <p>Se ha alcanzado el límite máximo de sesiones.</p>
                </div>
            </div>
        <form action="" onsubmit="sendMessage(event)">
            <div class="form-group">
                <h2>Tu ID de sesion es: <span id="ws-id"></span></h2>
                <div class="col-8">
                    <div id="message-container" style="display: none;">
                        <div class="input-group mb-3">
                            <input type="text" class="form-control" type="text" id="messageText" autocomplete="off">
                            <div class="input-group-append">
                                <button class="btn btn-outline-secondary" type="button">Enviar</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </form>
        <ul class="list-group" id='messages'>
        </ul>
        </div>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws;
            
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
            function connectWebSocket() {
                var nickname = document.getElementById("nickname").value;
                var client_id = Date.now();
                
                document.querySelector("#ws-id").textContent = client_id;
                ws = new WebSocket(`wss://chat-il81.onrender.com/ws/${client_id}`);
                document.getElementById("message-container").style.display = "block";
                document.getElementById("connectButton").disabled = true;
                document.getElementById("nickname").readOnly = true;
                 ws.onopen = function(event) {
                 
                    var message = event.data;
                    console.log(message)
                    if (message === "Límite de sesiones alcanzado. No se puede conectar.") {
                        // Muestra el mensaje de error
                        document.getElementById("errorMessage").style.display = "block";
                        // Cierra la conexión WebSocket
                        ws.close();
                    } 
                    ws.send("Usuario conectado");
                }
                ws.onmessage = function(event) {
                var message = event.data;
                console.log(message)
                    if (message === "Límite de sesiones alcanzado. No se puede conectar.") {
                        // Muestra el mensaje de error
                        document.getElementById("errorMessage").style.display = "block";
                        // Cierra la conexión WebSocket
                        ws.close();
                    } else {
                        var messages = document.getElementById('messages');
                        var message = document.createElement('li');
                        message.classList.add("list-group-item");
                        var content = document.createTextNode(event.data);
                        message.appendChild(content);
                        messages.appendChild(message);
                    }
                };
            }
        </script>
    </body>
</html>
"""
def verificar_limite_sesiones():
    return len(active_sessions) < 2  # Limita a dos sesiones activas

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int,  nickname: str):
    if not verificar_limite_sesiones():
        await websocket.send_text("Límite de sesiones alcanzado. No se puede conectar.")
        await websocket.close(code=4000, reason="Límite de sesiones alcanzado")
        return
    await manager.connect(websocket)
    active_sessions.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()

            if data == "Usuario conectado":
                # Envía un mensaje de bienvenida o notificación a todos los demás usuarios conectados
                await manager.broadcast(f"{nickname} se ha conectado")
                data = ""

            personal_message = f"Tu: {data}"
            broadcast_message = f"Usuario #{nickname} dice: {data}"
            
            # Obtén una lista de IDs de clientes conectados
            connected_client_ids = [conn.path_params["client_id"] for conn in manager.active_connections]
            
            for connection in manager.active_connections:
                if connection == websocket:
                    # Envía el mensaje personal solo al remitente
                    await manager.send_personal_message(personal_message, connection)
                elif connection.path_params["client_id"] in connected_client_ids:
                    # Envía el mensaje de difusión a otros clientes
                    await manager.send_personal_message(broadcast_message, connection)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        active_sessions.remove(websocket)
        await manager.broadcast(f"Usuario #{client_id} se desconectó")
