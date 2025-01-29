import asyncio
import webview
from g4f.client import Client
import json
import time
import os
import logging
import sys
import webbrowser

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

class Api:
    def __init__(self, history_file='chat_history.json'):
        self.client = Client()
        self.history_file = os.path.join(os.path.expanduser("~"), 'SnarkyAI', history_file)
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        self.chat_history = self.load_history()
        self.current_chat = None
        self.loading_states = {'text': False, 'image': False}

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                logging.debug(f"Chat history successfully loaded from {self.history_file}.")
                return history
            except Exception as e:
                logging.error(f"Error loading chat history: {e}")
                return []
        else:
            logging.debug("Chat history file not found. Creating a new file.")
            return []

    def save_history_to_file(self):
        try:
            absolute_path = os.path.abspath(self.history_file)
            logging.debug(f"Saving chat history to: {absolute_path}")
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.chat_history, f, ensure_ascii=False, indent=4)
            logging.debug("Chat history successfully saved.")
        except Exception as e:
            logging.error(f"Error saving chat history: {e}")

    def generate_text(self, model, prompt):
        if self.loading_states['text']:
            logging.debug("Text generation already in progress. Skipping new request.")
            return "Generation in progress..."
    
        self.loading_states['text'] = True
        try:
            if self.current_chat is None:
                logging.debug("Creating a new chat.")
                new_chat = {'timestamp': time.time(), 'messages': []}
                self.chat_history.append(new_chat)
                self.current_chat = new_chat['messages']

            user_message = {'user': prompt}
            self.current_chat.append(user_message)
            logging.debug(f"Added user message: {prompt}")

            messages = [{"role": "user", "content": prompt}]
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                web_search=False
            )
            ai_response = response.choices[0].message.content.strip()
            ai_message = {'ai': ai_response}
            self.current_chat.append(ai_message)
            logging.debug(f"Received AI response: {ai_response}")

            self.save_history_to_file()

            return ai_response
        except Exception as e:
            logging.error(f"Error generating text: {e}")
            return f"Error: {str(e)}"
        finally:
            self.loading_states['text'] = False

    def generate_image(self, model, prompt):
        if self.loading_states['image']:
            logging.debug("Image generation already in progress. Skipping new request.")
            return "Generation in progress..."
    
        self.loading_states['image'] = True
        try:
            if self.current_chat is None:
                logging.debug("Creating a new chat.")
                new_chat = {'timestamp': time.time(), 'messages': []}
                self.chat_history.append(new_chat)
                self.current_chat = new_chat['messages']

            user_message = {'user': prompt}
            self.current_chat.append(user_message)
            logging.debug(f"Added user message: {prompt}")

            response = self.client.images.generate(
                model=model,
                prompt=prompt,
                response_format="url"
            )
            image_url = response.data[0].url.strip()
            image_message = {'image': image_url}
            self.current_chat.append(image_message)
            logging.debug(f"Received image: {image_url}")

            self.save_history_to_file()

            return image_url
        except Exception as e:
            logging.error(f"Error generating image: {e}")
            return f"Error: {str(e)}"
        finally:
            self.loading_states['image'] = False

    def get_history(self):
        return json.dumps(self.chat_history)

    def save_chat(self):
        if self.current_chat:
            logging.debug("Saving current chat.")
            self.save_history_to_file()
            self.current_chat = None
            logging.debug("Current chat cleared for a new session.")
        else:
            logging.debug("No active chat to save.")

    def load_chat(self, messages):
        if messages:
            logging.debug("Loading selected chat.")
            self.current_chat = messages
            self.save_history_to_file()
            logging.debug("Selected chat loaded and saved.")
        else:
            logging.debug("No messages to load.")
            self.current_chat = None

    def open_url(self, url):
        try:
            webbrowser.open(url)
            logging.debug(f"Opened URL in browser: {url}")
        except Exception as e:
            logging.error(f"Failed to open URL {url}: {e}")

html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SnarkyAI</title>
    <style>
        :root {
            --primary: #2e2e2e;
            --secondary: #1a1a1a;
            --background: #1e1e1e;
            --text: #e0e0e0;
            --highlight: #2a2a2a;
            --copy-button-bg: #444444;
            --copy-button-hover-bg: #333333;
            --button-text-color: #ffffff;
            --notification-bg: rgba(0, 0, 0, 0.7);
            --notification-text: #ffffff;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', system-ui, sans-serif;
        }

        body {
            background: var(--background);
            color: var(--text);
            height: 100vh;
            overflow: hidden;
        }

        .container {
            display: flex;
            height: 100vh;
            position: relative;
            transition: transform 0.3s ease;
        }

        .sidebar {
            width: 300px;
            background: var(--highlight);
            padding: 20px;
            position: fixed;
            height: 100%;
            left: -300px;
            transition: 0.3s all cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 1000;
            border-right: 1px solid var(--secondary);
            overflow-y: auto;
        }

        .sidebar.active {
            left: 0;
        }

        .chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 20px;
            position: relative;
            transition: margin-left 0.3s ease;
        }

        .top-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
            position: sticky;
            top: 0;
            z-index: 100;
            background: var(--highlight);
            padding: 10px 20px;
            border-radius: 8px;
        }

        .top-text {
            font-size: 14px;
            color: var(--text);
            opacity: 0.8;
            flex: 1;
            text-align: center;
        }

        .header {
            display: flex;
            gap: 15px;
        }

        .sidebar.active + .chat-container {
            margin-left: 300px;
        }

        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            margin-bottom: 80px;
        }

        .message {
            max-width: 70%;
            padding: 15px 20px;
            border-radius: 20px;
            animation: messageAppear 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            background: var(--highlight);
            transition: transform 0.2s, opacity 0.2s;
            box-shadow: 0 5px 15px rgba(0,0,0,0.5);
        }

        .message:hover {
            transform: translateY(-2px);
        }

        .message.user {
            align-self: flex-end;
            background: var(--primary);
            border-bottom-right-radius: 5px;
        }

        .message.ai {
            align-self: flex-start;
            background: var(--secondary);
            border-bottom-left-radius: 5px;
        }

        .message.error {
            align-self: center;
            background: #ff4d4d;
            border-radius: 10px;
        }

        .message-image {
            max-width: 100%;
            border-radius: 15px;
            margin-top: 10px;
            transform: scale(0.9);
            opacity: 0;
            animation: imageAppear 0.5s 0.2s forwards;
            box-shadow: 0 10px 30px rgba(0,0,0,0.7);
            cursor: pointer;
            transition: transform 0.3s;
        }

        .message-image:hover {
            transform: scale(1.02);
        }

        .input-container {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 20px;
            background: linear-gradient(transparent, var(--background) 70%);
            display: flex;
            gap: 10px;
            backdrop-filter: blur(5px);
        }

        input, button {
            padding: 12px 20px;
            border: none;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.1);
            color: var(--text);
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            font-size: 14px;
            border: 1px solid transparent;
        }

        button {
            background: var(--primary);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            position: relative;
            overflow: hidden;
            color: var(--button-text-color);
        }

        button.copy-btn {
            background: var(--copy-button-bg);
            padding: 8px 12px;
            font-size: 12px;
            border-radius: 8px;
            margin-left: 10px;
        }

        button.copy-btn:hover {
            background: var(--copy-button-hover-bg);
        }

        button::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            background: rgba(255,255,255,0.1);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            transition: width 0.3s, height 0.3s;
        }

        button:active::after {
            width: 200px;
            height: 200px;
        }

        button:active {
            transform: scale(0.95);
        }

        .model-selector {
            position: relative;
            display: inline-block;
        }

        .model-button {
            background: rgba(255,255,255,0.1);
            padding: 10px 20px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.2s;
            color: var(--text);
        }

        .model-button:hover {
            background: rgba(255,255,255,0.15);
        }

        .model-list {
            position: absolute;
            top: 110%;
            right: 0;
            background: var(--background);
            border-radius: 10px;
            padding: 10px;
            min-width: 200px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.7);
            opacity: 0;
            transform: translateY(-10px);
            visibility: hidden;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 1000;
        }

        .model-list.active {
            opacity: 1;
            transform: translateY(0);
            visibility: visible;
        }

        .model-option {
            padding: 12px 16px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            color: var(--text);
        }

        .model-option:hover {
            background: rgba(255,255,255,0.05);
        }

        .loader {
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255, 255, 255, 0.2);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes messageAppear {
            from {
                transform: translateY(20px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        @keyframes imageAppear {
            to {
                transform: scale(1);
                opacity: 1;
            }
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .menu-button {
            background: var(--primary);
            border: none;
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: transform 0.2s;
            color: var(--button-text-color);
        }

        .menu-button.active {
            transform: rotate(90deg);
        }

        .menu-button:active {
            transform: scale(0.9);
        }

        .history-item, .new-chat-item {
            padding: 12px;
            margin: 8px 0;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            color: var(--text);
        }

        .history-item:hover, .new-chat-item:hover {
            background: rgba(255,255,255,0.1);
            transform: translateX(5px);
        }

        .notification {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--notification-bg);
            color: var(--notification-text);
            padding: 10px 20px;
            border-radius: 5px;
            opacity: 0;
            transition: opacity 0.5s;
            z-index: 1002;
            pointer-events: none;
        }

        pre {
            background: #2c2c2c;
            padding: 10px 40px 10px 10px;
            border-radius: 8px;
            overflow-x: auto;
            position: relative;
            max-width: 100%;
            color: #e0e0e0;
            font-family: 'Courier New', Courier, monospace;
        }

        code {
            color: #e0e0e0;
            font-family: 'Courier New', Courier, monospace;
        }

        .code-container {
            position: relative;
        }

        .copy-code-btn {
            position: absolute;
            top: 5px;
            right: 5px;
            background: var(--copy-button-bg);
            padding: 4px 8px;
            font-size: 10px;
            border-radius: 4px;
            cursor: pointer;
            color: var(--button-text-color);
            transition: background 0.2s;
        }

        .copy-code-btn:hover {
            background: var(--copy-button-hover-bg);
        }

    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar" id="sidebar">
            <h2>Chat History</h2>
            <div id="history-list" class="history-list">
                <div class="new-chat-item" onclick="startNewChat()">Start New Chat</div>
            </div>
        </div>

        <div class="chat-container" id="chat-container">
            <div class="top-bar">
                <button class="menu-button" id="menu-button" onclick="toggleSidebar()">☰</button>
                
                <div class="top-text">SnarkyAI beta v1</div>
                
                <div class="header">
                    <div class="model-selector">
                        <button class="model-button" onclick="toggleModelMenu('text')">
                            <span id="text-model-label">GPT-4</span>
                            <span class="arrow">▼</span>
                        </button>
                        <div class="model-list" id="text-model-list">
                            <div class="model-option" onclick="selectModel('text', 'gpt-4', 'GPT-4')">GPT-4</div>
                            <div class="model-option" onclick="selectModel('text', 'gpt-4o-mini', 'GPT-4o-Mini')">GPT-4o-Mini</div>
                            <div class="model-option" onclick="selectModel('text', 'claude-3.5-sonnet', 'Claude 3.5 Sonnet')">Claude 3.5 Sonnet</div>
                            <div class="model-option" onclick="selectModel('text', 'claude-3.5-haiku', 'Claude 3.5 Haiku')">Claude 3.5 Haiku</div>
                            <div class="model-option" onclick="selectModel('text', 'blackboxai', 'BlackBoxAI')">BlackBoxAI</div>
                            <div class="model-option" onclick="selectModel('text', 'mixtral-7b', 'Mixtral-7B')">Mixtral-7B</div>
                            <div class="model-option" onclick="selectModel('text', 'mistral-nemo', 'Mistral Nemo')">Mistral Nemo</div>
                        </div>
                    </div>

                    <div class="model-selector">
                        <button class="model-button" onclick="toggleModelMenu('image')">
                            <span id="image-model-label">DALL-E 3</span>
                            <span class="arrow">▼</span>
                        </button>
                        <div class="model-list" id="image-model-list">
                            <div class="model-option" onclick="selectModel('image', 'dall-e-3', 'DALL-E 3')">DALL-E 3</div>
                            <div class="model-option" onclick="selectModel('image', 'flux', 'Flux')">Flux</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="messages" id="messages"></div>

            <div class="input-container">
                <input type="text" id="input" placeholder="Type your message..." style="flex:1">
                <button onclick="generateText()" id="text-btn">
                    <span>Generate Text</span>
                </button>
                <button onclick="generateImage()" id="image-btn">
                    <span>Generate Image</span>
                </button>
            </div>
        </div>
    </div>

    <div id="notification" class="notification"></div>

    <script>
        let isGenerating = false;
        let activeModelMenu = null;
        let lastUserPrompt = null;

        async function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const menuButton = document.getElementById('menu-button');
            sidebar.classList.toggle('active');
            menuButton.classList.toggle('active');

            if (sidebar.classList.contains('active')) {
                await updateHistory();
            }
        }

        function toggleModelMenu(type) {
            const menu = document.getElementById(`${type}-model-list`);
            if (activeModelMenu && activeModelMenu !== menu) {
                activeModelMenu.classList.remove('active');
            }
            menu.classList.toggle('active');
            activeModelMenu = menu.classList.contains('active') ? menu : null;
        }

        function selectModel(type, value, label) {
            document.getElementById(`${type}-model-label`).textContent = label;
            document.getElementById(`${type}-model-list`).classList.remove('active');
            activeModelMenu = null;
        }

        function closeAllModelMenus() {
            document.querySelectorAll('.model-list').forEach(menu => {
                menu.classList.remove('active');
            });
            activeModelMenu = null;
        }

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.model-selector')) {
                closeAllModelMenus();
            }
        });

        async function generateText() {
            if (isGenerating) return;
            isGenerating = true;
            
            const input = document.getElementById('input');
            const modelLabel = document.getElementById('text-model-label').textContent;
            const modelMap = {
                'GPT-4': 'gpt-4',
                'GPT-4o-Mini': 'gpt-4o-mini',
                'Claude 3.5 Sonnet': 'claude-3.5-sonnet',
                'Claude 3.5 Haiku': 'claude-3.5-haiku',
                'BlackBoxAI': 'blackboxai',
                'Mixtral-7B': 'mixtral-7b',
                'Mistral Nemo': 'mistral-nemo'
            };
            const model = modelMap[modelLabel] || 'gpt-4';
            const prompt = input.value.trim();
            if (!prompt) {
                isGenerating = false;
                return;
            }

            lastUserPrompt = prompt;

            addMessage(prompt, 'user');
            input.value = '';
            
            const btn = document.getElementById('text-btn');
            btn.style.opacity = '0.8';
            btn.style.pointerEvents = 'none';
            const loader = createLoader();
            btn.appendChild(loader);
            
            try {
                const response = await window.pywebview.api.generate_text(model, prompt);
                if (response.startsWith("Error:")) {
                    addMessage(response, 'error');
                } else {
                    addAIMessage(response);
                }
            } catch (e) {
                addMessage(`Error: ${e}`, 'error');
            }
            
            loader.remove();
            btn.style.opacity = '1';
            btn.style.pointerEvents = 'all';
            isGenerating = false;
        }

        async function generateImage() {
            if (isGenerating) return;
            isGenerating = true;
            
            const input = document.getElementById('input');
            const modelLabel = document.getElementById('image-model-label').textContent;
            const modelMap = {
                'DALL-E 3': 'dall-e-3',
                'Flux': 'flux'
            };
            const model = modelMap[modelLabel] || 'dall-e-3';
            const prompt = input.value.trim();
            if (!prompt) {
                isGenerating = false;
                return;
            }

            lastUserPrompt = prompt;

            addMessage(prompt, 'user');
            input.value = '';
            
            const btn = document.getElementById('image-btn');
            btn.style.opacity = '0.8';
            btn.style.pointerEvents = 'none';
            const loader = createLoader();
            btn.appendChild(loader);
            
            try {
                const url = await window.pywebview.api.generate_image(model, prompt);
                if (url.startsWith("Error:")) {
                    addMessage(url, 'error');
                } else {
                    addImage(url);
                }
            } catch (e) {
                addMessage(`Error: ${e}`, 'error');
            }
            
            loader.remove();
            btn.style.opacity = '1';
            btn.style.pointerEvents = 'all';
            isGenerating = false;
        }

        function addMessage(text, type) {
            const messages = document.getElementById('messages');
            const message = document.createElement('div');
            message.className = `message ${type}`;
            message.textContent = text;

            messages.appendChild(message);
            messages.scrollTop = messages.scrollHeight;
        }

        function addAIMessage(text) {
            const messages = document.getElementById('messages');
            const message = document.createElement('div');
            message.className = 'message ai';

            const codeRegex = /`([^`]+)`/g;
            let match;
            let lastIndex = 0;
            const fragments = [];

            while ((match = codeRegex.exec(text)) !== null) {
                if (match.index > lastIndex) {
                    const textBefore = text.substring(lastIndex, match.index);
                    if (textBefore.trim() !== '') {
                        fragments.push(document.createTextNode(textBefore));
                    }
                }

                const codeContainer = document.createElement('div');
                codeContainer.className = 'code-container';

                const pre = document.createElement('pre');
                const code = document.createElement('code');
                code.textContent = match[1];
                pre.appendChild(code);
                codeContainer.appendChild(pre);

                const copyCodeBtn = document.createElement('button');
                copyCodeBtn.className = 'copy-code-btn';
                copyCodeBtn.textContent = 'Copy';
                copyCodeBtn.addEventListener('click', () => copyText(match[1]));
                codeContainer.appendChild(copyCodeBtn);

                fragments.push(codeContainer);

                lastIndex = codeRegex.lastIndex;
            }

            if (lastIndex < text.length) {
                const remainingText = text.substring(lastIndex);
                if (remainingText.trim() !== '') {
                    fragments.push(document.createTextNode(remainingText));
                }
            }

            fragments.forEach(fragment => {
                message.appendChild(fragment);
            });

            messages.appendChild(message);
            messages.scrollTop = messages.scrollHeight;
        }

        function addImage(url) {
            const messages = document.getElementById('messages');
            const container = document.createElement('div');
            container.className = 'message ai';
            
            const img = document.createElement('img');
            img.src = url;
            img.className = 'message-image';
            img.title = 'Click to open in browser';

            img.addEventListener('click', () => window.pywebview.api.open_url(url));

            container.appendChild(img);

            messages.appendChild(container);
            messages.scrollTop = messages.scrollHeight;
        }

        function createLoader() {
            const loader = document.createElement('div');
            loader.className = 'loader';
            return loader;
        }

        async function updateHistory() {
            const historyList = document.getElementById('history-list');
            historyList.innerHTML = '';

            const newChatItem = document.createElement('div');
            newChatItem.className = 'new-chat-item';
            newChatItem.textContent = 'Start New Chat';
            newChatItem.onclick = () => startNewChat();
            historyList.appendChild(newChatItem);

            try {
                const history = JSON.parse(await window.pywebview.api.get_history());
                history.forEach((chat, index) => {
                    const item = document.createElement('div');
                    item.className = 'history-item';
                    const date = new Date(chat.timestamp * 1000).toLocaleString();
                    item.textContent = `Chat ${index + 1} - ${date}`;
                    item.onclick = () => loadChat(chat);
                    historyList.appendChild(item);
                });
            } catch (e) {
                console.error('Failed to load history:', e);
                showTemporaryNotification('Failed to load chat history');
            }
        }

        async function loadChat(chat) {
            const messages = document.getElementById('messages');
            messages.innerHTML = '';
            chat.messages.forEach(msg => {
                if (msg.user) {
                    addMessage(msg.user, 'user');
                }
                if (msg.ai) {
                    addAIMessage(msg.ai);
                }
                if (msg.image) {
                    addImage(msg.image);
                }
            });

            await window.pywebview.api.load_chat(chat.messages);
        }

        async function startNewChat() {
            await window.pywebview.api.save_chat();

            const messages = document.getElementById('messages');
            messages.innerHTML = '';
            showTemporaryNotification('New chat started');
        }

        function copyText(text) {
            navigator.clipboard.writeText(text).then(() => {
                showTemporaryNotification('Copied to clipboard');
            }).catch(err => {
                showTemporaryNotification('Failed to copy');
                console.error('Clipboard copy failed:', err);
            });
        }

        function showTemporaryNotification(message) {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.style.opacity = '1';
            notification.style.pointerEvents = 'auto';

            setTimeout(() => {
                notification.style.opacity = '0';
                
                setTimeout(() => {
                    notification.textContent = '';
                    notification.style.pointerEvents = 'none';
                }, 500);
            }, 2000);
        }

        document.getElementById('input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                generateText();
            }
        });
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    api = Api()
    window = webview.create_window(
        'SnarkyAI by mlwr.e',
        html=html,
        js_api=api,
        min_size=(800, 600),
        background_color='#1e1e1e',
    )
    webview.start(debug=False)
