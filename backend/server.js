const express = require('express');
const cors = require('cors');
const admin = require('firebase-admin');

const serviceAccount = require('./serviceAccountKey.json');

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

if (!admin.apps.length) {
    admin.initializeApp({
        credential: admin.credential.cert(serviceAccount)
    });
}
const db = admin.firestore();

app.post('/alert', async (req, res) => {
    try {
        const data = req.body;
        data.server_time = new Date().toISOString();
        
        // Save alert
        await db.collection('alerts').add(data);
        
        console.log(`[${data.os}] Alert: ${data.event}`);
        res.json({ status: "success" });
    } catch (e) {
        res.status(500).send(e.message);
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
