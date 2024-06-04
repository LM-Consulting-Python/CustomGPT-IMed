import express from 'express';
import path from 'path';
import multer from 'multer';
import axios from 'axios';
import FormData from 'form-data';

const app = express();
const PORT = 3000;

const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

app.use(express.static('public'));
app.use(express.json());

app.get('/', (req, res) => {
    res.sendFile(path.resolve('public/index.html'));
});

app.post('/api/create-assistant', upload.array('files'), async (req, res) => {
    try {
        const { name, instructions, model, temperature, top_p } = req.body;
        const files = req.files;

        const formData = new FormData();
        formData.append('name', name);
        formData.append('instructions', instructions);
        formData.append('model', model);
        formData.append('temperature', temperature);
        formData.append('top_p', top_p);

        files.forEach(file => {
            formData.append('files', file.buffer, {
                filename: file.originalname,
                contentType: file.mimetype
            });
        });

        const response = await axios.post('http://localhost:8000/api/create-assistant', formData, {
            headers: {
                ...formData.getHeaders()
            }
        });

        res.json(response.data);
    } catch (error) {
        console.error(error);
        res.status(500).send('Erro ao criar assistente.');
    }
});

app.listen(PORT, () => {
    console.log(`Servidor rodando em http://localhost:${PORT}`);
});
