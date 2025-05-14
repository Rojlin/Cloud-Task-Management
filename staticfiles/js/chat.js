/**
 * Enhanced Chat Functionality
 */
console.log("Loading ChatApp class definition...");

class ChatApp {
    constructor(options) {
        console.log("ChatApp constructor called with options:", options);
        
        this.chatRoomId = options.chatRoomId;
        this.currentUser = options.currentUser;
        this.messagesContainer = document.getElementById('chat-messages');
        this.messageForm = document.getElementById('chat-form');
        this.messageInput = document.getElementById('chat-message-input');
        this.emojiButton = document.getElementById('emoji-button');
        this.emojiPicker = document.getElementById('emoji-picker');
        this.fileInput = document.getElementById('file-input');
        this.typingIndicator = document.getElementById('typing-indicator');
        this.typingTimeout = null;
        this.chatSocket = null;
        this.isTyping = false;
        this.reactions = ['👍', '❤️', '😂', '😮', '😢', '👏'];
        this.typingUsers = new Set();
        
        // Check if all required elements are found
        if (!this.messagesContainer) console.error("Message container not found!");
        if (!this.messageForm) console.error("Message form not found!");
        if (!this.messageInput) console.error("Message input not found!");
        if (!this.typingIndicator) console.error("Typing indicator not found!");
        
        // Initialize only if we have the required elements
        if (this.messagesContainer && this.messageForm && this.messageInput) {
            this.initializeChat();
        } else {
            console.error("Cannot initialize chat - required elements missing");
        }
    }
    
    initializeChat() {
        console.log("Initializing chat with room ID:", this.chatRoomId);
        this.connectWebSocket();
        this.bindEvents();
        this.scrollToBottom();
        this.loadMessageReactions();
        this.setupEmojiPicker();
    }
    
    connectWebSocket() {
        // Explicitly use ws or wss based on the current protocol
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/chat/${this.chatRoomId}/`;
        console.log('Attempting to connect to WebSocket at:', wsUrl);
        
        // Close existing connection if any
        if (this.chatSocket && this.chatSocket.readyState !== WebSocket.CLOSED) {
            console.log('Closing existing WebSocket connection');
            this.chatSocket.close();
        }
        
        try {
            this.chatSocket = new WebSocket(wsUrl);
            
            this.chatSocket.onopen = (e) => {
                console.log('Chat WebSocket connection established successfully');
                this.setConnectionStatus(true);
                this.showNotification('Connected to chat server', 'success');
                
                // Send a ping every 30 seconds to keep the connection alive
                this.pingInterval = setInterval(() => {
                    if (this.chatSocket.readyState === WebSocket.OPEN) {
                        this.chatSocket.send(JSON.stringify({
                            'type': 'ping'
                        }));
                    }
                }, 30000);
            };
            
            this.chatSocket.onclose = (e) => {
                console.error('Chat WebSocket connection closed with code:', e.code, 'reason:', e.reason);
                this.setConnectionStatus(false);
                this.showNotification('Connection lost. Reconnecting...', 'warning');
                
                // Clear ping interval
                if (this.pingInterval) {
                    clearInterval(this.pingInterval);
                }
                
                // Try to reconnect after 3 seconds
                setTimeout(() => this.connectWebSocket(), 3000);
            };
            
            this.chatSocket.onerror = (e) => {
                console.error('WebSocket error occurred:', e);
                this.showNotification('Connection error. Attempting to reconnect...', 'danger');
            };
            
            this.chatSocket.onmessage = (e) => {
                console.log('Received message data:', e.data);
                try {
                    const data = JSON.parse(e.data);
                    console.log('Parsed message data:', data);
                    
                    switch(data.type) {
                        case 'message':
                            // For regular chat messages
                            const isCurrentUser = data.user_id === this.currentUser.id;
                            this.addMessage(data.message, data.username, isCurrentUser, data.timestamp);
                            
                            // Play notification sound if message is from other user
                            if (!isCurrentUser) {
                                this.playMessageSound();
                            }
                            
                            this.scrollToBottom();
                            break;
                            
                        case 'system':
                            // For system messages (user joined/left)
                            this.addSystemMessage(data.message);
                            this.scrollToBottom();
                            break;
                            
                        case 'typing':
                            // Show typing indicator
                            if (data.user_id !== this.currentUser.id) {
                                if (data.is_typing) {
                                    this.addTypingUser(data.username, data.user_id);
                                } else {
                                    this.removeTypingUser(data.user_id);
                                }
                                this.updateTypingIndicator();
                            }
                            break;
                        case 'reaction':
                            // Update message reaction
                            this.updateMessageReaction(data.message_id, data.reaction, data.user_id);
                            break;
                            
                        case 'error':
                            // Handle error messages
                            this.showNotification(data.message, 'danger');
                            break;
                            
                        case 'ping':
                            // Respond to ping with pong
                            if (this.chatSocket.readyState === WebSocket.OPEN) {
                                this.chatSocket.send(JSON.stringify({ 'type': 'pong' }));
                            }
                            break;
                            
                        default:
                            console.log('Unknown message type:', data.type);
                    }
                } catch (error) {
                    // Parse error handling
                    console.error('Error parsing message:', error, e.data);
                    this.showNotification('Error processing message', 'danger');
                }
            }
        };
        
        this.chatSocket.onerror = (e) => {
            console.error('Chat WebSocket error:', e);
            this.showNotification('Connection error. Please try refreshing the page.', 'danger');
        };
    }
    
    bindEvents() {
        // Send message on form submit
        this.messageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const message = this.messageInput.value.trim();
            if (message) {
                this.sendMessage(message);
                this.messageInput.value = '';
                this.stopTyping();
            }
        });
        
        // Typing indicator
        this.messageInput.addEventListener('input', () => {
            if (!this.isTyping) {
                this.isTyping = true;
                this.sendTypingIndicator();
            }
            
            // Reset typing timeout
            clearTimeout(this.typingTimeout);
            this.typingTimeout = setTimeout(() => {
                this.isTyping = false;
                this.stopTyping();
            }, 3000);
        });
        
        // Handle emoji button click
        if (this.emojiButton) {
            this.emojiButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleEmojiPicker();
            });
        }
        
        // Handle file button click
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleFileUpload(e.target.files[0]);
                }
            });
        }
        
        // Handle document clicks (close emoji picker when clicking outside)
        document.addEventListener('click', (e) => {
            if (this.emojiPicker && this.emojiPicker.classList.contains('visible') && 
                !this.emojiPicker.contains(e.target) && 
                e.target !== this.emojiButton) {
                this.emojiPicker.classList.remove('visible');
            }
        });
        
        // Handle message reactions
        this.messagesContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('chat-reaction-btn')) {
                const messageId = e.target.closest('.chat-message').dataset.messageId;
                const reaction = e.target.dataset.reaction;
                this.toggleReaction(messageId, reaction);
            }
        });
    }
    
    sendMessage(message) {
        // Get message from input if not provided
        if (!message && this.messageInput) {
            message = this.messageInput.value.trim();
        }
        
        // Don't send empty messages
        if (!message) {
            return;
        }
        
        console.log('Attempting to send message:', message);
        
        if (this.chatSocket && this.chatSocket.readyState === WebSocket.OPEN) {
            try {
                // Use type property for proper message handling on the server
                const data = JSON.stringify({ 
                    'type': 'message', 
                    'message': message 
                });
                console.log('Sending data:', data);
                this.chatSocket.send(data);
                console.log('Message sent successfully');
                
                // Clear the input after sending
                if (this.messageInput) {
                    this.messageInput.value = '';
                    this.messageInput.focus();
                }
                
                // Stop typing indicator
                this.stopTyping();
            } catch (error) {
                console.error('Error sending message:', error);
                this.showNotification('Error sending message. Please try again.', 'danger');
            }
        } else {
            console.error('WebSocket not connected, state:', this.chatSocket ? this.chatSocket.readyState : 'null');
            this.showNotification('Connection lost. Reconnecting...', 'warning');
            
            // Try to reconnect and queue the message
            this.connectWebSocket();
            setTimeout(() => {
                if (this.chatSocket && this.chatSocket.readyState === WebSocket.OPEN) {
                    this.sendMessage(message);
                }
            }, 1000);
        }
    }
    
    sendTypingIndicator() {
        if (this.chatSocket && this.chatSocket.readyState === WebSocket.OPEN) {
            this.chatSocket.send(JSON.stringify({
                'typing': true
            }));
        }
    }
    
    stopTyping() {
        if (this.chatSocket && this.chatSocket.readyState === WebSocket.OPEN) {
            this.chatSocket.send(JSON.stringify({
                'typing': false
            }));
        }
    }
    
    addMessage(message, sender, isOutgoing, timestamp) {
        const messageId = Date.now(); // Use timestamp as temporary ID
        const messageElement = document.createElement('div');
        messageElement.className = `chat-message ${isOutgoing ? 'outgoing' : 'incoming'}`;
        messageElement.dataset.messageId = messageId;
        
        // Format timestamp
        const messageDate = timestamp ? new Date(timestamp) : new Date();
        const formattedTime = this.formatTime(messageDate);
        
        // Check if we need to add a date divider
        this.addDateDividerIfNeeded(messageDate);
        
        // Format message with emojis and links
        const formattedMessage = this.formatMessageContent(message);
        
        messageElement.innerHTML = `
            <div class="chat-message-content">
                ${formattedMessage}
            </div>
            <div class="chat-message-meta">
                <span class="chat-message-sender">${sender}</span>
                <span class="chat-message-time">${formattedTime}</span>
            </div>
            <div class="chat-message-actions">
                <div class="chat-message-reactions"></div>
                <div class="chat-reaction-toolbar">
                    ${this.reactions.map(emoji => 
                        `<button class="chat-reaction-btn" data-reaction="${emoji}">${emoji}</button>`
                    ).join('')}
                </div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageElement);
        
        // Animation for new message
        setTimeout(() => {
            messageElement.classList.add('visible');
        }, 10);
    }
    
    addSystemMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'chat-system-message';
        
        messageElement.innerHTML = `
            <span>${message}</span>
        `;
        
        this.messagesContainer.appendChild(messageElement);
    }
    
    // Add a user to the typing users list
    addTypingUser(username, userId) {
        this.typingUsers.add(userId);
        this.updateTypingIndicator();
    }
    
    // Remove a user from the typing users list
    removeTypingUser(userId) {
        this.typingUsers.delete(userId);
        this.updateTypingIndicator();
    }
    
    // Update the typing indicator based on who is typing
    updateTypingIndicator() {
        if (!this.typingIndicator) return;
        
        // If no one is typing, hide the indicator
        if (this.typingUsers.size === 0) {
            this.typingIndicator.classList.remove('visible');
            return;
        }
        
        // Get all typing usernames
        const typingUsernames = Array.from(this.typingUsers);
        let message = '';
        
        if (typingUsernames.length === 1) {
            message = `${typingUsernames[0]} is typing`;
        } else if (typingUsernames.length === 2) {
            message = `${typingUsernames[0]} and ${typingUsernames[1]} are typing`;
        } else {
            message = `${typingUsernames.length} people are typing`;
        }
        
        this.typingIndicator.innerHTML = `
            <span>${message}</span>
            <span class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </span>
        `;
        this.typingIndicator.classList.add('visible');
    }
    
    // Send typing indicator to server
    sendTypingIndicator() {
        if (this.chatSocket && this.chatSocket.readyState === WebSocket.OPEN) {
            console.log('Sending typing indicator (typing)');
            this.chatSocket.send(JSON.stringify({
                'type': 'typing',
                'typing': true
            }));
        }
    }
    
    // Send stop typing indicator to server
    stopTyping() {
        if (this.isTyping && this.chatSocket && this.chatSocket.readyState === WebSocket.OPEN) {
            console.log('Sending typing indicator (stopped typing)');
            this.chatSocket.send(JSON.stringify({
                'type': 'typing',
                'typing': false
            }));
            this.isTyping = false;
        }
    }
    
    // Handle user typing
    handleTyping() {
        if (!this.isTyping) {
            this.isTyping = true;
            this.sendTypingIndicator();
        }
        
        // Reset the typing timeout
        clearTimeout(this.typingTimeout);
        this.typingTimeout = setTimeout(() => {
            this.stopTyping();
        }, 3000);
    }
    
    toggleEmojiPicker() {
        if (this.emojiPicker) {
            this.emojiPicker.classList.toggle('visible');
        }
    }
    
    setupEmojiPicker() {
        if (this.emojiPicker) {
            // Populate with common emojis
            const commonEmojis = ['😀', '😂', '😍', '👍', '👎', '❤️', '🔥', '🎉', '👏', '😊', '🙏', '🤔', '😢', '😎', '😁'];
            
            let emojiHtml = '';
            for (const emoji of commonEmojis) {
                emojiHtml += `<span class="emoji-item" data-emoji="${emoji}">${emoji}</span>`;
            }
            
            this.emojiPicker.innerHTML = emojiHtml;
            
            // Add event listeners
            const emojiItems = this.emojiPicker.querySelectorAll('.emoji-item');
            emojiItems.forEach(item => {
                item.addEventListener('click', () => {
                    const emoji = item.dataset.emoji;
                    this.insertEmoji(emoji);
                    this.toggleEmojiPicker();
                });
            });
        }
    }
    
    insertEmoji(emoji) {
        const cursorPos = this.messageInput.selectionStart;
        const textBefore = this.messageInput.value.substring(0, cursorPos);
        const textAfter = this.messageInput.value.substring(cursorPos);
        
        this.messageInput.value = textBefore + emoji + textAfter;
        
        // Place cursor after inserted emoji
        this.messageInput.selectionStart = cursorPos + emoji.length;
        this.messageInput.selectionEnd = cursorPos + emoji.length;
        this.messageInput.focus();
    }
    
    handleFileUpload(file) {
        // Check file size (max 5MB)
        if (file.size > 5 * 1024 * 1024) {
            this.showNotification('File size must be less than 5MB', 'danger');
            return;
        }
        
        // Handle file type
        if (file.type.startsWith('image/')) {
            this.uploadImage(file);
        } else {
            this.showNotification('Only image files are supported', 'warning');
        }
    }
    
    uploadImage(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const imageUrl = e.target.result;
            // Send image as base64 string
            this.sendMessage(`[Image: ${file.name}]\n${imageUrl}`);
        };
        reader.readAsDataURL(file);
    }
    
    toggleReaction(messageId, reaction) {
        if (this.chatSocket && this.chatSocket.readyState === WebSocket.OPEN) {
            this.chatSocket.send(JSON.stringify({
                'reaction': reaction,
                'message_id': messageId
            }));
        }
    }
    
    updateMessageReaction(messageId, reaction, userId) {
        const messageElement = document.querySelector(`.chat-message[data-message-id="${messageId}"]`);
        if (!messageElement) return;
        
        let reactionsContainer = messageElement.querySelector('.chat-message-reactions');
        
        // Check if reaction already exists
        const existingReaction = reactionsContainer.querySelector(`[data-reaction="${reaction}"][data-user="${userId}"]`);
        
        if (existingReaction) {
            // Remove reaction
            existingReaction.remove();
        } else {
            // Add new reaction
            const reactionElement = document.createElement('span');
            reactionElement.className = 'chat-message-reaction';
            reactionElement.dataset.reaction = reaction;
            reactionElement.dataset.user = userId;
            reactionElement.innerHTML = `${reaction} <span class="reaction-count">1</span>`;
            reactionsContainer.appendChild(reactionElement);
        }
    }
    
    loadMessageReactions() {
        // This would typically fetch existing reactions from server
        // For now, just a placeholder
    }
    
    formatMessageContent(message) {
        // Replace URLs with clickable links
        let formattedMessage = message.replace(
            /(https?:\/\/[^\s]+)/g, 
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        // Handle image messages
        if (message.startsWith('[Image:') && message.includes('data:image/')) {
            const imageName = message.split('[Image:')[1].split(']')[0].trim();
            const base64Data = message.split('\n')[1];
            
            formattedMessage = `
                <div class="chat-image-message">
                    <img src="${base64Data}" alt="${imageName}" class="chat-image" />
                    <div class="chat-image-caption">${imageName}</div>
                </div>
            `;
        }
        
        return formattedMessage;
    }
    
    addDateDividerIfNeeded(date) {
        const dateStr = this.formatDate(date);
        const lastDivider = this.messagesContainer.querySelector('.chat-date-divider:last-of-type');
        
        // Check if we already have a divider for this date
        if (lastDivider && lastDivider.dataset.date === dateStr) {
            return false;
        }
        
        // Add new date divider
        const dividerElement = document.createElement('div');
        dividerElement.className = 'chat-date-divider';
        dividerElement.dataset.date = dateStr;
        dividerElement.innerHTML = `<span>${dateStr}</span>`;
        
        this.messagesContainer.appendChild(dividerElement);
        return true;
    }
    
    formatDate(date) {
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        if (date.toDateString() === today.toDateString()) {
            return 'Today';
        } else if (date.toDateString() === yesterday.toDateString()) {
            return 'Yesterday';
        } else {
            return date.toLocaleDateString('en-US', { 
                weekday: 'long', 
                month: 'short', 
                day: 'numeric'
            });
        }
    }
    
    formatTime(date) {
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit'
        });
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }
    
    setConnectionStatus(isConnected) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.className = isConnected ? 'status-connected' : 'status-disconnected';
            statusElement.title = isConnected ? 'Connected' : 'Disconnected';
        }
    }
    
    showNotification(message, type = 'info') {
        // Create notification if it doesn't exist
        let notification = document.getElementById('chat-notification');
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'chat-notification';
            notification.className = 'chat-notification';
            document.body.appendChild(notification);
        }
        
        // Set message and type
        notification.textContent = message;
        notification.className = `chat-notification chat-notification-${type}`;
        
        // Show notification
        notification.classList.add('visible');
        
        // Hide after 3 seconds
        setTimeout(() => {
            notification.classList.remove('visible');
        }, 3000);
    }
    
    playMessageSound() {
        // Play notification sound
        try {
            const audio = new Audio('/static/audio/message.mp3');
            audio.volume = 0.5;
            audio.play();
        } catch (error) {
            console.log('Could not play notification sound');
        }
    }
}

// Initialize chat when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a chat page
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer && window.chatRoomId && window.currentUser) {
        window.chatApp = new ChatApp({
            chatRoomId: window.chatRoomId,
            currentUser: window.currentUser
        });
    }
});