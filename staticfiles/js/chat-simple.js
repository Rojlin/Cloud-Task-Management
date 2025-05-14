/**
 * Simple Chat Functionality - For debugging purposes
 */
console.log("Loading chat-simple.js");

// Create a global ChatApp class for testing
class ChatApp {
    constructor(options) {
        console.log("ChatApp constructor called with:", options);
        this.chatRoomId = options.chatRoomId;
        this.currentUser = options.currentUser;
        this.messagesToSend = [];
        
        // Setup WebSocket connection
        this.connectWebSocket();
        
        // Bind form submission
        const form = document.getElementById('chat-form');
        if (form) {
            console.log("Found chat form, binding submit event");
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendMessage();
            });
        } else {
            console.error("Chat form not found!");
        }
        
        // Bind typing events to input
        const input = document.getElementById('chat-message-input');
        if (input) {
            console.log("Found message input, binding events");
            input.addEventListener('input', () => {
                this.sendTypingIndicator(true);
                
                // Clear previous timeout
                if (this.typingTimeout) {
                    clearTimeout(this.typingTimeout);
                }
                
                // Set timeout to stop typing
                this.typingTimeout = setTimeout(() => {
                    this.sendTypingIndicator(false);
                }, 3000);
            });
        } else {
            console.error("Message input not found!");
        }
    }
    
    connectWebSocket() {
        console.log("Connecting to WebSocket...");
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.chatRoomId}/`;
        
        console.log("WebSocket URL:", wsUrl);
        
        try {
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = (e) => {
                console.log("WebSocket connection established");
                
                // Send any queued messages
                if (this.messagesToSend.length > 0) {
                    this.messagesToSend.forEach(msg => {
                        this.socket.send(JSON.stringify(msg));
                    });
                    this.messagesToSend = [];
                }
            };
            
            this.socket.onclose = (e) => {
                console.log("WebSocket connection closed:", e.code, e.reason);
                setTimeout(() => this.connectWebSocket(), 3000);
            };
            
            this.socket.onerror = (e) => {
                console.error("WebSocket error:", e);
            };
            
            this.socket.onmessage = (e) => {
                console.log("Received message:", e.data);
                try {
                    const data = JSON.parse(e.data);
                    
                    if (data.type === 'message') {
                        this.addMessageToUI(data.message, data.username, data.user_id === this.currentUser.id);
                    } else if (data.type === 'typing') {
                        this.updateTypingIndicator(data.username, data.is_typing);
                    } else if (data.type === 'system') {
                        this.addSystemMessage(data.message);
                    }
                } catch (err) {
                    console.error("Error parsing message:", err);
                }
            };
        } catch (err) {
            console.error("Error connecting to WebSocket:", err);
        }
    }
    
    sendMessage() {
        const input = document.getElementById('chat-message-input');
        if (!input) return;
        
        const message = input.value.trim();
        if (!message) return;
        
        console.log("Sending message:", message);
        
        const messageData = {
            type: 'message',
            message: message
        };
        
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(messageData));
            input.value = '';
            
            // Stop typing indicator
            this.sendTypingIndicator(false);
        } else {
            // Queue the message to send when connection is established
            this.messagesToSend.push(messageData);
            this.connectWebSocket();
        }
    }
    
    sendTypingIndicator(isTyping) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'typing',
                typing: isTyping
            }));
        }
    }
    
    addMessageToUI(message, sender, isCurrentUser) {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isCurrentUser ? 'outgoing' : 'incoming'}`;
        
        messageDiv.innerHTML = `
            <div class="chat-message-content">${message}</div>
            <div class="chat-message-meta">
                <span class="chat-message-sender">${sender}</span>
                <span class="chat-message-time">${new Date().toLocaleTimeString()}</span>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    updateTypingIndicator(username, isTyping) {
        const indicator = document.getElementById('typing-indicator');
        if (!indicator) return;
        
        if (isTyping) {
            indicator.innerHTML = `
                <span>${username} is typing</span>
                <span class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </span>
            `;
            indicator.classList.add('visible');
        } else {
            indicator.classList.remove('visible');
        }
    }
    
    addSystemMessage(message) {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-system-message';
        messageDiv.textContent = message;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Initialize chat when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded, initializing chat");
    
    // Check if we're on a chat page
    if (window.chatRoomId && window.currentUser) {
        console.log("Chat page detected, creating ChatApp");
        window.chatApp = new ChatApp({
            chatRoomId: window.chatRoomId,
            currentUser: window.currentUser
        });
    } else {
        console.log("Not a chat page or missing required data");
    }
});