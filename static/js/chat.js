document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const typingIndicator = document.getElementById('typing-indicator');
    
    // Store chat history
    let chatHistory = [];
    
    // Display initial bot message
    displayBotMessage(
        "Olá! I'm your Brazilian Housing Laws Assistant. How can I help you with tenant rights, " +
        "rental obligations, or housing disputes in Brazil today?",
        []
    );
    
    // Handle form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = userInput.value.trim();
        
        if (message) {
            // Display user message
            displayUserMessage(message);
            
            // Add to chat history
            chatHistory.push(message);
            
            // Clear input
            userInput.value = '';
            
            // Show typing indicator
            typingIndicator.style.display = 'flex';
            
            // Send to server
            sendMessageToServer(message);
        }
    });
    
    function displayUserMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', 'user-message');
        messageElement.innerHTML = `
            <div class="message-content">
                <p>${escapeHtml(message)}</p>
            </div>
        `;
        chatMessages.appendChild(messageElement);
        scrollToBottom();
    }
    
    function displayBotMessage(message, citations) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', 'bot-message');
        
        // Process message text (convert line breaks and format citations)
        const formattedMessage = formatMessage(message);
        
        let citationsHtml = '';
        if (citations && citations.length > 0) {
            citationsHtml = `
                <div class="citations">
                    <h6>References:</h6>
                    <ul>
                        ${citations.map(citation => `<li><a href="${citation}" target="_blank">${citation}</a></li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        messageElement.innerHTML = `
            <div class="message-content">
                <div class="bot-icon">
                    <i class="fas fa-balance-scale"></i>
                </div>
                <div>
                    ${formattedMessage}
                    ${citationsHtml}
                </div>
            </div>
        `;
        
        chatMessages.appendChild(messageElement);
        
        // Add to chat history
        if (chatHistory.length % 2 === 1) {
            // Only add bot message if it's responding to a user message
            chatHistory.push(message);
        }
        
        scrollToBottom();
    }
    
    function formatMessage(text) {
        // Convert line breaks to <br> tags
        let formatted = text.replace(/\n/g, '<br>');
        
        // Format law citations (like "Lei nº 8.245/91" or "Art. 22")
        formatted = formatted.replace(/(Lei\s+nº\s+[\d\.]+\/\d+)/gi, '<strong>$1</strong>');
        formatted = formatted.replace(/(Art\.\s+\d+)/gi, '<strong>$1</strong>');
        
        return formatted;
    }
    
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function sendMessageToServer(message) {
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                history: chatHistory
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide typing indicator
            typingIndicator.style.display = 'none';
            
            if (data.error) {
                displayBotMessage(`Sorry, I encountered an error: ${data.error}`, []);
            } else {
                displayBotMessage(data.response, data.citations);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            typingIndicator.style.display = 'none';
            displayBotMessage("Sorry, I'm having trouble connecting to my knowledge base. Please try again later.", []);
        });
    }
    
    // Helper function to escape HTML
    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
