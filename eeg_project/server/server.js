// -------------------------
// Importaciones
// -------------------------
const express = require("express");
const mysql = require("mysql2");
const { SerialPort } = require("serialport");
const { ReadlineParser } = require("@serialport/parser-readline");
const cors = require("cors");

// -------------------------
// Configuración MySQL
// -------------------------
const db = mysql.createConnection({
  host: "localhost",
  user: "root",         // <-- cambia según tu MySQL
  password: "",         // <-- tu contraseña
  database: "eeg_db"
});

db.connect(err => {
  if (err) {
    console.error("❌ Error conectando a MySQL:", err);
    return;
  }
  console.log("✅ Conectado a MySQL");
});

db.query(`
  CREATE TABLE IF NOT EXISTS eeg_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    delta FLOAT,
    theta FLOAT,
    alpha FLOAT,
    beta FLOAT,
    gamma FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )
`);

// -------------------------
// Configuración Serial (Arduino)
// -------------------------
const port = new SerialPort({ path: "COM3", baudRate: 9600 }); 
// ⚠️ En Linux/Mac suele ser "/dev/ttyUSB0" o "/dev/ttyACM0"

const parser = port.pipe(new ReadlineParser({ delimiter: "\n" }));

parser.on("data", line => {
  try {
    const data = JSON.parse(line.trim());
    console.log("📥 Recibido:", data);

    db.query(
      "INSERT INTO eeg_data (delta, theta, alpha, beta, gamma) VALUES (?, ?, ?, ?, ?)",
      [data.delta, data.theta, data.alpha, data.beta, data.gamma],
      (err) => {
        if (err) console.error("❌ Error insertando:", err);
      }
    );

  } catch (err) {
    console.error("❌ Error parseando JSON:", line);
  }
});

// -------------------------
// Express API
// -------------------------
const app = express();
app.use(cors());

app.get("/api/data", (req, res) => {
  db.query("SELECT * FROM eeg_data ORDER BY created_at DESC", (err, results) => {
    if (err) return res.status(500).send(err);
    res.json(results);
  });
});

app.get("/api/latest", (req, res) => {
  db.query("SELECT * FROM eeg_data ORDER BY created_at DESC LIMIT 1", (err, results) => {
    if (err) return res.status(500).send(err);
    res.json(results[0]);
  });
});

// -------------------------
// Iniciar servidor
// -------------------------
const PORT = 3000;
app.listen(PORT, () => {
  console.log(`🚀 Servidor corriendo en http://localhost:${PORT}`);
});
