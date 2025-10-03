import { SerialPort, ReadlineParser } from 'serialport';
import express from 'express';
import http from 'http';
import { Server as IOServer } from 'socket.io';
import mysql from 'mysql2/promise';
import fft from 'fft-js';

const SERIAL_PORT = 'COM3'; // <-- CAMBIA según tu PC (Linux: /dev/ttyUSB0)
const BAUDRATE = 115200;
const SAMPLE_RATE = 256;
const BLOCK_SIZE = 256; // tamaño de bloque (potencia de 2 para FFT)

// Conexión a Arduino
const port = new SerialPort({ path: SERIAL_PORT, baudRate: BAUDRATE });
const parser = port.pipe(new ReadlineParser({ delimiter: '\n' }));

// Express + Socket.IO
const app = express();
const server = http.createServer(app);
const io = new IOServer(server, { cors: { origin: '*' } });
app.use(express.json());

// MySQL
const pool = mysql.createPool({
  host: 'localhost',
  user: 'root',
  password: 'tu_pass',
  database: 'eeg_db'
});

function computeBandPowers(samples) {
  const n = samples.length;
  const mean = samples.reduce((a,b)=>a+b,0)/n;
  const sig = samples.map(v => v - mean);
  const ph = fft.fft(sig);
  const mags = fft.util.fftMag(ph);
  const freqs = Array.from({length: mags.length}, (_,k) => k * SAMPLE_RATE / n);
  const bands = { delta:0, theta:0, alpha:0, beta:0, gamma:0 };
  for (let i=0;i<mags.length/2;i++){
    const f = freqs[i];
    const p = mags[i]*mags[i];
    if (f>=0.5 && f<4) bands.delta += p;
    else if (f>=4 && f<8) bands.theta += p;
    else if (f>=8 && f<13) bands.alpha += p;
    else if (f>=13 && f<30) bands.beta += p;
    else if (f>=30 && f<100) bands.gamma += p;
  }
  return bands;
}

let buffer = [];

parser.on('data', async (line) => {
  const val = parseInt(line.trim());
  if (isNaN(val)) return;
  buffer.push(val);

  if (buffer.length >= BLOCK_SIZE) {
    const block = buffer.splice(0, BLOCK_SIZE);
    try {
      const conn = await pool.getConnection();
      const [res] = await conn.query(
        'INSERT INTO raw_blocks (sample_rate, samples) VALUES (?, ?)',
        [SAMPLE_RATE, JSON.stringify(block)]
      );
      const rawId = res.insertId;
      const bands = computeBandPowers(block);
      await conn.query(
        'INSERT INTO band_powers (raw_block_id, delta, theta, alpha, beta, gamma) VALUES (?, ?, ?, ?, ?, ?)',
        [rawId, bands.delta, bands.theta, bands.alpha, bands.beta, bands.gamma]
      );
      conn.release();
      io.emit('band_update', { rawId, bands, ts: new Date() });
      console.log('Bloque guardado', rawId, bands);
    } catch (err) {
      console.error(err);
    }
  }
});

server.listen(3000, () => console.log("Servidor en http://localhost:3000"));
