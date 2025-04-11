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
        [],
        null
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
    
    function displayBotMessage(message, citations, queryId) {
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
        
        // Create feedback component if query ID exists
        let feedbackHtml = '';
        if (queryId) {
            feedbackHtml = `
                <div class="feedback-component mt-2" data-query-id="${queryId}">
                    <div class="feedback-question mb-1">Was this response helpful?</div>
                    <div class="feedback-stars">
                        <span class="star" data-rating="1"><i class="far fa-star"></i></span>
                        <span class="star" data-rating="2"><i class="far fa-star"></i></span>
                        <span class="star" data-rating="3"><i class="far fa-star"></i></span>
                        <span class="star" data-rating="4"><i class="far fa-star"></i></span>
                        <span class="star" data-rating="5"><i class="far fa-star"></i></span>
                    </div>
                    <div class="feedback-comments mt-2 d-none">
                        <textarea class="form-control form-control-sm" placeholder="Any additional comments? (optional)"></textarea>
                        <button class="btn btn-sm btn-primary mt-1 submit-feedback">Submit</button>
                    </div>
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
                    ${feedbackHtml}
                </div>
            </div>
        `;
        
        chatMessages.appendChild(messageElement);
        
        // Add event listeners for feedback stars
        if (queryId) {
            const feedbackComponent = messageElement.querySelector('.feedback-component');
            const stars = feedbackComponent.querySelectorAll('.star');
            const commentsSection = feedbackComponent.querySelector('.feedback-comments');
            
            stars.forEach(star => {
                star.addEventListener('mouseover', function() {
                    const rating = parseInt(this.getAttribute('data-rating'));
                    highlightStars(stars, rating);
                });
                
                star.addEventListener('mouseout', function() {
                    const selectedRating = feedbackComponent.getAttribute('data-selected-rating');
                    if (selectedRating) {
                        highlightStars(stars, parseInt(selectedRating));
                    } else {
                        resetStars(stars);
                    }
                });
                
                star.addEventListener('click', function() {
                    const rating = parseInt(this.getAttribute('data-rating'));
                    feedbackComponent.setAttribute('data-selected-rating', rating);
                    highlightStars(stars, rating);
                    commentsSection.classList.remove('d-none');
                });
            });
            
            // Submit feedback button
            const submitButton = feedbackComponent.querySelector('.submit-feedback');
            submitButton.addEventListener('click', function() {
                const rating = feedbackComponent.getAttribute('data-selected-rating');
                const comments = feedbackComponent.querySelector('textarea').value;
                
                submitFeedback(queryId, rating, comments, feedbackComponent);
            });
        }
        
        // Add to chat history
        if (chatHistory.length % 2 === 1) {
            // Only add bot message if it's responding to a user message
            chatHistory.push(message);
        }
        
        scrollToBottom();
    }
    
    function highlightStars(stars, rating) {
        stars.forEach(star => {
            const starRating = parseInt(star.getAttribute('data-rating'));
            if (starRating <= rating) {
                star.innerHTML = '<i class="fas fa-star text-warning"></i>';
            } else {
                star.innerHTML = '<i class="far fa-star"></i>';
            }
        });
    }
    
    function resetStars(stars) {
        stars.forEach(star => {
            star.innerHTML = '<i class="far fa-star"></i>';
        });
    }
    
    function submitFeedback(queryId, rating, comments, feedbackComponent) {
        fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query_id: queryId,
                rating: rating,
                comments: comments
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Replace feedback component with thank you message
                feedbackComponent.innerHTML = `
                    <div class="alert alert-success py-2">
                        <i class="fas fa-check-circle me-2"></i>Thank you for your feedback!
                    </div>
                `;
            } else {
                console.error('Error submitting feedback:', data.error);
                feedbackComponent.innerHTML += `
                    <div class="alert alert-danger py-2 mt-2">
                        Error submitting feedback. Please try again.
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            feedbackComponent.innerHTML += `
                <div class="alert alert-danger py-2 mt-2">
                    Error submitting feedback. Please try again.
                </div>
            `;
        });
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
                displayBotMessage(`Sorry, I encountered an error: ${data.error}`, [], null);
            } else {
                displayBotMessage(data.response, data.citations, data.query_id);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            typingIndicator.style.display = 'none';
            displayBotMessage("Sorry, I'm having trouble connecting to my knowledge base. Please try again later.", [], null);
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
