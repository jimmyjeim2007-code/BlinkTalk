import os
from flask import Flask, render_template_string, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from werkzeug.utils import secure_filename

app = Flask("BlinkTalkProfile")
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ROOM_PASSWORD = "123"
active_groups = ["General Chat", "Tech Support"]

HTML_PAGE = '''
<!doctype html>
<html>
<head>
    <title>BlinkTalk - Profile & Group Chat</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { background: #0f172a; color: #fff; font-family: Arial, sans-serif; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .card { width: 100%; max-width: 450px; background: #1e293b; padding: 25px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); text-align: center; }
        h2 { color: #38bdf8; margin-bottom: 20px; }
        input, button, select { width: 100%; padding: 12px; margin-top: 10px; background: #0f172a; border: 1px solid #334155; color: #fff; border-radius: 6px; box-sizing: border-box; font-size: 15px; }
        button { background: #2563eb; border: none; font-weight: bold; cursor: pointer; transition: 0.3s; }
        button:hover { background: #1d4ed8; }
        .main-container { display: flex; gap: 10px; text-align: left; }
        .sidebar { width: 40%; background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 10px; height: 300px; overflow-y: auto; }
        .chat-area { width: 60%; display: flex; flex-direction: column; }
        .chat-box { height: 240px; background: #0f172a; border: 1px solid #334155; border-radius: 6px; overflow-y: scroll; padding: 10px; margin-bottom: 10px; display: flex; flex-direction: column; }
        .message { background: #334155; padding: 8px 12px; border-radius: 6px; margin-bottom: 8px; max-width: 85%; word-break: break-all; display: flex; align-items: center; gap: 8px; }
        .message img { width: 30px; height: 30px; border-radius: 50%; object-fit: cover; }
        .message div span { font-size: 11px; color: #38bdf8; display: block; margin-bottom: 2px; font-weight: bold; }
        .group-item { padding: 8px; font-size: 14px; border-bottom: 1px solid #334155; cursor: pointer; color: #38bdf8; border-radius: 4px; margin-bottom: 4px; }
        .group-item:hover { background: #334155; }
        .hidden { display: none; }
        .input-group { display: flex; gap: 5px; }
        .input-group input { margin-top: 0; }
        .input-group button { width: auto; margin-top: 0; }
        .error { color: #ef4444; font-size: 13px; margin-top: 8px; display: none; }
        .file-label { display: block; margin-top: 10px; background: #334155; padding: 10px; border-radius: 6px; cursor: pointer; font-size: 14px; color: #38bdf8; }
        .file-label input { display: none; }
    </style>
</head>
<body>

    <!-- login with profile picture -->
    <div class="card" id="loginScreen">
        <h2>BlinkTalk Messenger</h2>
        <p style="color: #94a3b8; font-size: 14px;">Enter Name & Password</p>
        <input type="text" id="usernameInput" placeholder="Your Name..." required>
        
        <label class="file-label">
            📁 Select Profile Picture
            <input type="file" id="profilePicInput" accept="image/*">
        </label>
        
        <input type="password" id="passwordInput" placeholder="Room Password (123)..." required>
        <button onclick="startApp()">Next</button>
        <p class="error" id="errorMsg">Incorrect Password!</p>
    </div>

    <!-- group select -->
    <div class="card hidden" id="groupScreen">
        <h2>Select or Create Group</h2>
        <select id="groupSelect"></select>
        <p style="margin: 15px 0 5px 0; color: #94a3b8; font-size: 13px;">Or create a new group:</p>
        <input type="text" id="newGroupName" placeholder="New Group Name...">
        <button onclick="joinSelectedGroup()">Join / Create Group</button>
    </div>

    <!-- chat room -->
    <div class="card hidden" id="chatScreen" style="max-width: 650px;">
        <h2 id="roomTitle" style="font-size: 18px; margin-bottom: 10px;">Group Chat</h2>
        <div class="main-container">
            <div class="sidebar">
                <p style="font-size:12px; color:#94a3b8; margin:0 0 5px 0; font-weight:bold;">Available Groups:</p>
                <div id="groupListSidebar"></div>
            </div>
            <div class="chat-area">
                <div class="chat-box" id="messages"></div>
                <div class="input-group">
                    <input type="text" id="myMessage" placeholder="Type message...">
                    <button onclick="sendMessage()">Send</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        var socket = io();
        var myName = "";
        var myAvatar = "";
        var currentGroup = "";
        var correctPassword = "{{ password }}";

        function startApp() {
            var inputName = document.getElementById('usernameInput').value.trim();
            var inputPass = document.getElementById('passwordInput').value.trim();
            var fileInput = document.getElementById('profilePicInput');
            var errTag = document.getElementById('errorMsg');

            if(inputName === "" || inputPass === "") {
                alert("Fill all required fields!");
                return;
            }

            if(inputPass === correctPassword) {
                myName = inputName;
                
                if(fileInput.files.length > 0) {
                    var formData = new FormData();
                    formData.append("file", fileInput.files[0]);

                    fetch('/upload', { method: 'POST', body: formData })
                    .then(res => res.json())
                    .then(data => {
                        myAvatar = "/uploads/" + data.filename;
                        proceedToGroups();
                    });
                } else {
                    myAvatar = "https://via.placeholder.com/30";
                    proceedToGroups();
                }
            } else {
                errTag.style.display = "block";
            }
        }

        function proceedToGroups() {
            socket.emit('get_groups');
            document.getElementById('loginScreen').classList.add('hidden');
            document.getElementById('groupScreen').classList.remove('hidden');
        }

        socket.on('load_groups', function(groups) {
            var select = document.getElementById('groupSelect');
            var sidebar = document.getElementById('groupListSidebar');
            select.innerHTML = "";
            sidebar.innerHTML = "";

            groups.forEach(function(g) {
                var opt = document.createElement('option');
                opt.value = g;
                opt.innerText = g;
                select.appendChild(opt);

                var div = document.createElement('div');
                div.className = 'group-item';
                div.innerText = "# " + g;
                div.onclick = function() { switchGroup(g); };
                sidebar.appendChild(div);
            });
        });

        function joinSelectedGroup() {
            var selectedGrp = document.getElementById('groupSelect').value;
            var newGrp = document.getElementById('newGroupName').value.trim();
            
            currentGroup = newGrp !== "" ? newGrp : selectedGrp;
            
            socket.emit('join_group', { group: currentGroup, user: myName });
            
            document.getElementById('groupScreen').classList.add('hidden');
            document.getElementById('chatScreen').classList.remove('hidden');
            document.getElementById('roomTitle').innerText = "Group: " + currentGroup;
        }

        function switchGroup(groupName) {
            currentGroup = groupName;
            socket.emit('join_group', { group: currentGroup, user: myName });
            document.getElementById('roomTitle').innerText = "Group: " + currentGroup;
            document.getElementById('messages').innerHTML = "";
        }

        function sendMessage() {
            var input = document.getElementById('myMessage');
            if(input.value.trim() !== "") {
                socket.emit('outgoing_message', { group: currentGroup, user: myName, avatar: myAvatar, msg: input.value });
                input.value = '';
            }
        }

        socket.on('incoming_message', function(data) {
            var msgBox = document.getElementById('messages');
            var div = document.createElement('div');
            div.className = 'message';
            
            var avatarImg = data.avatar ? data.avatar : "https://via.placeholder.com/30";
            
            div.innerHTML = '<img src="' + avatarImg + '"><div><span>' + data.user + '</span>' + data.msg + '</div>';
            msgBox.appendChild(div);
            msgBox.scrollTop = msgBox.scrollHeight;
        });

        socket.on('update_groups', function(groups) {
            var sidebar = document.getElementById('groupListSidebar');
            var select = document.getElementById('groupSelect');
            sidebar.innerHTML = "";
            select.innerHTML = "";

            groups.forEach(function(g) {
                var opt = document.createElement('option');
                opt.value = g;
                opt.innerText = g;
                select.appendChild(opt);

                var div = document.createElement('div');
                div.className = 'group-item';
                div.innerText = "# " + g;
                div.onclick = function() { switchGroup(g); };
                sidebar.appendChild(div);
            });
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_PAGE, password=ROOM_PASSWORD)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return {'filename': ''}
    file = request.files['file']
    if file.filename == '':
        return {'filename': ''}
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return {'filename': filename}

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@socketio.on('get_groups')
def handle_get_groups():
    emit('load_groups', active_groups)

@socketio.on('join_group')
def handle_join_group(data):
    room = data['group']
    if room not in active_groups:
        active_groups.append(room)
        socketio.emit('update_groups', active_groups)
    
    join_room(room)
    emit('incoming_message', {'user': 'System', 'avatar': '', 'msg': f"{data['user']} joined the group."}, room=room)

@socketio.on('outgoing_message')
def handle_message(data):
    room = data['group']
    emit('incoming_message', {'user': data['user'], 'avatar': data['avatar'], 'msg': data['msg']}, room=room)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
