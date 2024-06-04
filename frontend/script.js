document.getElementById('create-assistant-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('name').value;
    const instructions = document.getElementById('instructions').value;
    const model = document.getElementById('model').value;
    const temperature = document.getElementById('temperature').value;
    const top_p = document.getElementById('top_p').value;

    const response = await fetch('/api/create-assistant', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name, instructions, model, temperature, top_p })
    });

    if (response.ok) {
        const result = await response.json();
        document.getElementById('assistantId').value = result.id;
        alert('Assistente criado com sucesso!');
    } else {
        const error = await response.json();
        alert('Erro ao criar assistente: ' + error.detail);
    }
});

document.getElementById('upload-files-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const assistantId = document.getElementById('assistantId').value;
    const files = document.getElementById('files').files;

    const formData = new FormData();
    formData.append('assistantId', assistantId);
    for (let file of files) {
        formData.append('files', file);
    }

    const response = await fetch('/api/upload-files', {
        method: 'POST',
        body: formData
    });

    if (response.ok) {
        const result = await response.json();
        console.log(result);
        alert('Arquivos enviados com sucesso!');
    } else {
        const error = await response.json();
        alert('Erro ao enviar arquivos: ' + error.detail);
    }
});

document.getElementById('files').addEventListener('change', (e) => {
    const files = e.target.files;
    const filesPreview = document.getElementById('files-preview');
    filesPreview.innerHTML = '';

    for (let file of files) {
        const fileReader = new FileReader();
        fileReader.onload = function(e) {
            const img = document.createElement('img');
            img.src = e.target.result;
            filesPreview.appendChild(img);
        };
        fileReader.readAsDataURL(file);
    }
});

document.getElementById('generate-vector-button').addEventListener('click', async () => {
    const assistantId = document.getElementById('assistantId').value;

    const response = await fetch('/api/generate-vector', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ assistantId })
    });

    if (response.ok) {
        const result = await response.json();
        console.log(result);
        alert('Vetor gerado com sucesso!');
    } else {
        const error = await response.json();
        alert('Erro ao gerar vetor: ' + error.detail);
    }
});
