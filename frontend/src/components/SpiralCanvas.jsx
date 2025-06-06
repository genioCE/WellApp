import React, { useEffect, useRef } from 'react';

/**
 * Minimal canvas-based 3D spiral visualization.
 * Provides a lightweight alternative to Three.js in offline environments.
 */
export default function SpiralCanvas({ memories = [], onSelect }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.clientWidth;
    const h = canvas.height = canvas.clientHeight;
    const centerX = w / 2;
    const centerY = h / 2;
    const fov = 300;

    ctx.clearRect(0, 0, w, h);
    memories.forEach((m, i) => {
      const angle = i * 0.3;
      const radius = 5 * i;
      const x3 = radius * Math.cos(angle);
      const y3 = radius * Math.sin(angle);
      const z3 = i * 5;
      const scale = fov / (fov + z3);
      const x2 = centerX + x3 * scale;
      const y2 = centerY + y3 * scale;
      const size = 4 * scale;
      ctx.beginPath();
      ctx.fillStyle = '#60a5fa';
      ctx.arc(x2, y2, size, 0, Math.PI * 2);
      ctx.fill();
    });
  }, [memories]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-40 border border-gray-700 mt-4"
    ></canvas>
  );
}
