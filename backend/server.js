const express = require('express');
const cors = require('cors');
const admin = require('firebase-admin');
const path = require('path');

// LOAD FIREBASE KEY
// Make sure serviceAccountKey.json is in this same folder!
const serviceAccount = require('./serviceAccountKey.json');

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static('public')); // Serves your dashboard

// INITIALIZE FIREBASE
if (!admin.apps.length) {
    admin.initializeApp({
        credential: admin.credential.cert(serviceAccount)
    });
}
const db = admin.firestore();

// API ENDPOINT
app.post('/alert', async (req, res) => {
    try {
        const data = req.body;
        // Add trusted server timestamp
        data.server_time = new Date().toISOString();
        
        // Save to Database
        await db.collection('alerts').add(data);
        
        console.log(`[LOG] ${data.os} Event: ${data.event} | File: ${data.file}`);
        res.json({ status: "success" });
    } catch (e) {
        console.error("Error:", e.message);
        res.status(500).send(e.message);
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🚀 Server running on port ${PORT}`));
