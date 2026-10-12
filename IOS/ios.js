
if (window.SO_Monitor) clearInterval(window.SO_Monitor);
console.clear();

console.log("%c[INFO] Inicializando Kernel y Módulos de Monitoreo...", "color: #3498db; font-weight: bold;");

// Variables para cálculos de rendimiento en tiempo real
let lastTime = performance.now();
let frameCount = 0;
let fps = 60;

// Medidor de FPS dinámico usando requestAnimationFrame
function medirFPS() {
    frameCount++;
    let currentTime = performance.now();
    if (currentTime - lastTime >= 1000) {
        fps = Math.round((frameCount * 1000) / (currentTime - lastTime));
        frameCount = 0;
        lastTime = currentTime;
    }
    requestAnimationFrame(medirFPS);
}
requestAnimationFrame(medirFPS);

window.SO_Monitor = setInterval(async () => {
    // 1. HARDWARE BÁSICO Y AVANZADO
    const cpuCores = navigator.hardwareConcurrency || 4;
    const deviceMemory = navigator.deviceMemory ? `${navigator.deviceMemory} GB (Aprox)` : "No expuesto por seguridad";
    
    // Memoria JS Heap (si el navegador lo soporta)
    let ramInfo = "No disponible";
    let ramPorcentaje = 0;
    if (performance.memory) {
        const usedMB = (performance.memory.usedJSHeapSize / 1024 / 1024).toFixed(2);
        const totalMB = (performance.memory.totalJSHeapSize / 1024 / 1024).toFixed(2);
        const limitMB = (performance.memory.jsHeapSizeLimit / 1024 / 1024).toFixed(2);
        ramInfo = `${usedMB} MB Usados / ${totalMB} MB Asignados (Límite: ${limitMB} MB)`;
        ramPorcentaje = ((performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit) * 100).toFixed(1);
    }

    // Información de Pantalla y GPU simulada por hardware
    const screenRes = `${window.screen.width}x${window.screen.height}`;
    const pixelRatio = window.devicePixelRatio || 1;
    const colorDepth = `${window.screen.colorDepth} bits`;

    // Estado de Batería (si el dispositivo la soporta)
    let bateriaEstado = "No disponible / Escritorio";
    if (navigator.getBattery) {
        try {
            const battery = await navigator.getBattery();
            bateriaEstado = `${(battery.level * 100).toFixed(0)}% (${battery.charging ? 'Cargando ⚡' : 'Descargando 🔋'})`;
        } catch(e) { }
    }

    // Estado de Red / Conectividad
    const conexion = navigator.connection ? `${navigator.connection.effectiveType.toUpperCase()} - Downlink: ${navigator.connection.downlink} Mbps - RTT: ${navigator.connection.rtt}ms` : "Desconocido";

    // 2. SOFTWARE Y PROCESOS SIMULADOS
    const uptimeOS = (performance.now() / 1000).toFixed(2);
    const userAgent = navigator.userAgent;
    const plataforma = navigator.platform;
    const language = navigator.language;

    // Simulación de carga de CPU basada en oscilación matemática y ruido aleatorio
    const cargaCPU = (12 + (Math.sin(performance.now() / 800) * 8) + (Math.random() * 6)).toFixed(1);

    // Listado simulado de procesos activos en el sistema operativo
    const procesosActivos = [
        { pid: 101, nombre: "kernel_task", estado: "Ejecutando", cpu: "2.1%", mem: "45 MB" },
        { pid: 204, nombre: "launchd / systemd", estado: "En espera", cpu: "0.1%", mem: "12 MB" },
        { pid: 315, nombre: "WindowServer / DWM", estado: "Ejecutando", cpu: `${(cargaCPU * 0.4).toFixed(1)}%`, mem: "120 MB" },
        { pid: 489, nombre: "Navegador (Proceso Principal)", estado: "Ejecutando", cpu: `${cargaCPU}%`, mem: performance.memory ? `${(performance.memory.usedJSHeapSize / 1024 / 1024).toFixed(1)} MB` : "85 MB" },
        { pid: 512, nombre: "Servicio de Red (NetworkManager)", estado: "En espera", cpu: "0.0%", mem: "8 MB" }
    ];

    // 3. LIMPIAR Y GENERAR REPORTE EN CONSOLA (Estilo Tabla y Grupos)
    console.clear();
    console.log("%c║        MONITOR DE RENDIMIENTO DEL SISTEMA OPERATIVO     ║", "color: #00ffcc; font-weight: bold;");

    console.log("\n%c [ 1. MONITOREO DE HARDWARE ]", "color: #f1c40f; font-weight: bold; font-size: 13px;");
    console.log(`  🔹 Núcleos lógicos CPU (Threads) : ${cpuCores} núcleos`);
    console.log(`  🔹 Arquitectura / Plataforma     : ${plataforma}`);
    console.log(`  🔹 Memoria RAM del Sistema       : ${deviceMemory}`);
    console.log(`  🔹 Memoria Heap de la App (JS)   : ${ramInfo} [${ramPorcentaje}% ocupado del límite]`);
    console.log(`  🔹 Resolución de Pantalla (GPU)  : ${screenRes} px (PixelRatio: ${pixelRatio}x, Color: ${colorDepth})`);
    console.log(`  🔹 Rendimiento Gráfico (FPS)     : ${fps} FPS (Renderizado activo)`);
    console.log(`  🔹 Estado de Energía / Batería   : ${bateriaEstado}`);

    console.log("\n%c [ 2. MONITOREO DE SOFTWARE Y Conectividad ]", "color: #f1c40f; font-weight: bold; font-size: 13px;");
    console.log(`  🔹 Tiempo Activo del SO (Uptime) : ${uptimeOS} segundos`);
    console.log(`  🔹 Carga Global Estimada de CPU  : ${cargaCPU}%`);
    console.log(`  🔹 Interfaz de Red (Conexión)    : ${conexion}`);
    console.log(`  🔹 Entorno / User Agent          : ${userAgent}`);
    console.log(`  🔹 Configuración Regional        : ${language}`);

    console.log("\n%c [ 3. TABLA DE PROCESOS ACTIVOS EN EL KERNEL ]", "color: #f1c40f; font-weight: bold; font-size: 13px;");
    console.table(procesosActivos);

    console.log("\n%c Para detener este script de monitoreo, escribe en la consola:", "color: #e74c3c; font-weight: bold;");
    console.log("%c   clearInterval(window.SO_Monitor);", "color: #2ecc71; font-weight: bold; background: #222; padding: 2px 5px; border-radius: 3px;");

}, 2000); // Se actualiza cada 2 segundos
