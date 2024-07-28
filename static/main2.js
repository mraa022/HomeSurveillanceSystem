document.addEventListener('DOMContentLoaded', function () {
    const dropZone = document.getElementById('drop-zone');
    const loadingScreen = document.getElementById('loading-screen');
    dropZone.addEventListener('dragover', function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFile(files[0]);
        }
    });

    function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        loadingScreen.style.display = 'flex';
        fetch('/search', {
            method: 'POST',
            body: formData
        })
        .then(response => response.text())
        .then(result => {
            loadingScreen.style.display = 'none';
            const json_result = JSON.parse(result)
            sessionStorage.setItem('matches', JSON.stringify(json_result.matches));
            // Redirect to the matches page
            window.location.href = '/matches';
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
});
