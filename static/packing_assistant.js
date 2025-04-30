document.addEventListener('DOMContentLoaded', function() {
    const packingEmailForm = document.getElementById('packingEmailForm');
    if (packingEmailForm) {
        packingEmailForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const submitButton = this.querySelector('button[type="submit"]');
            const originalButtonText = submitButton.innerHTML;
            
            // Disable button and show loading state
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
            
            fetch('/send-packing-list', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                const messageContainer = document.getElementById('emailMessage');
                if (data.success) {
                    messageContainer.innerHTML = '<div class="alert alert-success">' +
                        '<i class="fas fa-check-circle"></i> Packing list sent successfully!</div>';
                    document.getElementById('packingEmail').value = '';
                } else {
                    messageContainer.innerHTML = `<div class="alert alert-danger">` +
                        `<i class="fas fa-exclamation-circle"></i> Error: ${data.error}</div>`;
                }
            })
            .catch(error => {
                document.getElementById('emailMessage').innerHTML = 
                    '<div class="alert alert-danger">' +
                    '<i class="fas fa-exclamation-circle"></i> An error occurred while sending the email.</div>';
            })
            .finally(() => {
                // Restore button state
                submitButton.disabled = false;
                submitButton.innerHTML = originalButtonText;
            });
        });
    }
});