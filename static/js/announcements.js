/**
 * CollaboraSync Announcements Interaction
 * Handles like/comment button functionality on announcement cards
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get all like buttons
    const likeIcons = document.querySelectorAll('.announcement-action i.fa-thumbs-up');
    const likeButtons = Array.from(likeIcons).map(icon => icon.closest('.announcement-action'));
    
    // Get all comment buttons
    const commentIcons = document.querySelectorAll('.announcement-action i.fa-comment');
    const commentButtons = Array.from(commentIcons).map(icon => icon.closest('.announcement-action'));
    
    // Add click event to like buttons
    likeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Toggle active state for the button
            this.classList.toggle('liked');
            
            // Get the count span
            const countSpan = this.querySelector('span');
            
            // Get current count
            let count = parseInt(countSpan.textContent);
            
            // If liked, increment count, otherwise decrement
            if (this.classList.contains('liked')) {
                count += 1;
                // Change color to purple/blue
                this.style.color = '#8e44ad';
            } else {
                count -= 1;
                // Reset color to gray
                this.style.color = '#6c757d';
            }
            
            // Update the count
            countSpan.textContent = count;
        });
    });
    
    // Add click event to comment buttons
    commentButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Toggle active state for the button
            this.classList.toggle('commented');
            
            // Change color if commenting is active
            if (this.classList.contains('commented')) {
                this.style.color = '#3498db';
                
                // Show comment input if needed
                const card = this.closest('.announcement-card');
                let commentForm = card.querySelector('.comment-form');
                
                // Create comment form if it doesn't exist
                if (!commentForm) {
                    commentForm = document.createElement('div');
                    commentForm.className = 'comment-form mt-2 p-3 bg-light';
                    commentForm.innerHTML = `
                        <form>
                            <div class="form-group">
                                <textarea class="form-control mb-2" placeholder="Write a comment..."></textarea>
                                <button type="button" class="btn btn-sm btn-primary">Submit</button>
                                <button type="button" class="btn btn-sm btn-outline-secondary cancel-comment">Cancel</button>
                            </div>
                        </form>
                    `;
                    
                    // Add to the card
                    card.querySelector('.announcement-footer').after(commentForm);
                    
                    // Handle cancel button
                    commentForm.querySelector('.cancel-comment').addEventListener('click', () => {
                        commentForm.remove();
                        this.classList.remove('commented');
                        this.style.color = '#6c757d';
                    });
                    
                    // Handle submit button
                    commentForm.querySelector('.btn-primary').addEventListener('click', () => {
                        const commentText = commentForm.querySelector('textarea').value;
                        if (commentText.trim()) {
                            // Get current count and increment
                            const countSpan = this.querySelector('span');
                            let count = parseInt(countSpan.textContent);
                            count += 1;
                            countSpan.textContent = count;
                            
                            // Add the comment to the UI (in a real app, this would be saved to a database)
                            const commentsSection = card.querySelector('.comments-section');
                            if (!commentsSection) {
                                const newCommentsSection = document.createElement('div');
                                newCommentsSection.className = 'comments-section p-3 bg-light mt-2';
                                newCommentsSection.innerHTML = `
                                    <h6 class="mb-3 small text-muted">Comments</h6>
                                    <div class="comment mb-2">
                                        <div class="d-flex">
                                            <div class="me-2 announcement-avatar">
                                                <i class="fas fa-user"></i>
                                            </div>
                                            <div>
                                                <div class="small fw-bold">You</div>
                                                <div class="small">${commentText}</div>
                                                <div class="text-muted smallest">Just now</div>
                                            </div>
                                        </div>
                                    </div>
                                `;
                                card.querySelector('.announcement-footer').after(newCommentsSection);
                            } else {
                                const newComment = document.createElement('div');
                                newComment.className = 'comment mb-2';
                                newComment.innerHTML = `
                                    <div class="d-flex">
                                        <div class="me-2 announcement-avatar">
                                            <i class="fas fa-user"></i>
                                        </div>
                                        <div>
                                            <div class="small fw-bold">You</div>
                                            <div class="small">${commentText}</div>
                                            <div class="text-muted smallest">Just now</div>
                                        </div>
                                    </div>
                                `;
                                commentsSection.appendChild(newComment);
                            }
                            
                            // Remove the form
                            commentForm.remove();
                        }
                    });
                } else {
                    // If comment form already exists, just toggle its visibility
                    commentForm.style.display = commentForm.style.display === 'none' ? 'block' : 'none';
                }
            } else {
                // Reset color to gray
                this.style.color = '#6c757d';
                
                // Hide comment input if visible
                const card = this.closest('.announcement-card');
                const commentForm = card.querySelector('.comment-form');
                if (commentForm) {
                    commentForm.style.display = 'none';
                }
            }
        });
    });
});