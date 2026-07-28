// ==========================================
// 1. VARIABLES GLOBALES Y DEL DOM
// ==========================================
const selectUnidad = document.getElementById("unidadSelect");
const selectSubunidad = document.getElementById("subunidadSelect");
const infoRegistro = document.getElementById("info-registro");
const pasoApto = document.getElementById("paso-apto");
const btnGuardar = document.getElementById("btnGuardar");

// Variable CSRF Token para peticiones AJAX
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

// Modo de operación actual
let modoActual = 'visitante'; 

// Variables Visitantes
let tramaTemporal = "";
let esIngresoManual = false;
let documentoFinal = "";
let nombreFinal = "";
const moduloVisitantes = document.getElementById("modulo-visitantes");
const pasoEscaner = document.getElementById("paso-escaner");
const pasoDatosManuales = document.getElementById("paso-datos-manuales");
const inputEscaner = document.getElementById("escanerInput");
const comText = document.getElementById("comText");

// Variables Paquetería
const zonaPaquete = document.getElementById("zona-paquete");
const videoCamara = document.getElementById("videoCamara");
const canvasFoto = document.getElementById("canvasFoto");
let fotoCapturadaBase64 = null;
let streamCamara = null;

// ==========================================
// 2. SISTEMA DE PESTAÑAS (TABS)
// ==========================================
document.getElementById("btnModoPaquete").addEventListener("click", function() {
    modoActual = 'paquete';
    
    // Estética
    this.classList.add('activo');
    document.getElementById("btnModoVisita").classList.remove('activo');
    
    // Visibilidad
    moduloVisitantes.style.display = "none";
    zonaPaquete.style.display = "block";
    document.getElementById("extrasVisitante").style.display = "none"; 
    pasoApto.style.display = "none";
    
    // Encender cámara
    iniciarCamara();
});

document.getElementById("btnModoVisita").addEventListener("click", function() {
    modoActual = 'visitante';
    
    // Estética
    this.classList.add('activo');
    document.getElementById("btnModoPaquete").classList.remove('activo');
    
    // Visibilidad
    zonaPaquete.style.display = "none";
    moduloVisitantes.style.display = "block";
    document.getElementById("extrasVisitante").style.display = "block"; 
    pasoApto.style.display = "none";
    
    // Apagar cámara y resetear
    apagarCamara();
    reiniciarPantalla();
});


// ==========================================
// 3. MÓDULO DE CÁMARA (PAQUETERÍA)
// ==========================================
async function iniciarCamara() {
    try {
        streamCamara = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        videoCamara.srcObject = streamCamara;
        videoCamara.style.display = "block";
        canvasFoto.style.display = "none";
        document.getElementById("btnTomarFoto").style.display = "block";
        document.getElementById("btnRepetirFoto").style.display = "none";
        fotoCapturadaBase64 = null;
    } catch (err) {
        console.error("Error de cámara:", err);
        alert("⚠️ Por favor, permite el acceso a la cámara para tomar fotos a los paquetes.");
    }
}

function apagarCamara() {
    if (streamCamara) {
        streamCamara.getTracks().forEach(track => track.stop());
    }
}

document.getElementById("btnTomarFoto").addEventListener("click", () => {
    const context = canvasFoto.getContext('2d');
    canvasFoto.width = videoCamara.videoWidth;
    canvasFoto.height = videoCamara.videoHeight;
    context.drawImage(videoCamara, 0, 0, canvasFoto.width, canvasFoto.height);
    
    // Convertir a JPEG
    fotoCapturadaBase64 = canvasFoto.toDataURL('image/jpeg', 0.6); 
    
    videoCamara.style.display = "none";
    canvasFoto.style.display = "block";
    document.getElementById("btnTomarFoto").style.display = "none";
    document.getElementById("btnRepetirFoto").style.display = "block";
});

document.getElementById("btnRepetirFoto").addEventListener("click", () => {
    fotoCapturadaBase64 = null;
    videoCamara.style.display = "block";
    canvasFoto.style.display = "none";
    document.getElementById("btnTomarFoto").style.display = "block";
    document.getElementById("btnRepetirFoto").style.display = "none";
});

document.getElementById("btnContinuarPaquete").addEventListener("click", () => {
    if (!document.getElementById("empresaPaquete").value.trim()) {
        return alert("⚠️ Por favor, ingresa la Empresa de Mensajería.");
    }
   /* if (!fotoCapturadaBase64) {
        return alert("📸 Debes tomarle una foto al paquete o la guía.");
    }*/
    zonaPaquete.style.display = "none";
    pasoApto.style.display = "block";
});


// ==========================================
// 4. LÓGICA WEB SERIAL (PUERTO COM)
// ==========================================
let puerto;
let lector;

async function conectarLectorCOM() {
  try {
    puerto = await navigator.serial.requestPort();
    await puerto.open({ baudRate: 9600 });
    
    comText.innerText = "✅ Lector Conectado y Listo (COM)";
    comText.style.color = "#28a745";
    inputEscaner.placeholder = "Escáner activo. Pase la cédula...";
    inputEscaner.style.cursor = "text";

    const decoder = new TextDecoderStream();
    puerto.readable.pipeTo(decoder.writable);
    lector = decoder.readable.getReader();

    escucharLector();
  } catch (err) {
    alert("No se pudo conectar el escáner. Asegúrate de seleccionarlo en la lista y dar permisos.");
  }
}

async function escucharLector() {
  let buffer = "";
  while (true) {
    const { value, done } = await lector.read();
    if (done) break;
    if (value) {
      buffer += value;
      if (buffer.includes('\r') || buffer.includes('\n')) {
          let limpia = buffer.replace(/\x00/g, " ").replace(/[\x01-\x1F\x7F-\x9F]/g, "").replace(/\s+/g, " ").trim();
          if (limpia !== "") procesarEntradaEscaner(limpia);
          buffer = "";
      }
    }
  }
}

function procesarEntradaEscaner(trama) {
    tramaTemporal = trama;
    inputEscaner.value = trama;
    pasoEscaner.style.display = "none";
    pasoApto.style.display = "block";
    setTimeout(() => selectUnidad.focus(), 150);
}

comText.addEventListener("click", () => { if (!puerto) conectarLectorCOM(); });
inputEscaner.addEventListener("click", () => { if (!puerto) conectarLectorCOM(); });

async function intentarAutoConexion() {
  if ("serial" in navigator) {
    try {
      const ports = await navigator.serial.getPorts();
      if (ports.length > 0) {
        puerto = ports[0];
        await puerto.open({ baudRate: 9600 });
        comText.innerText = "✅ Lector Auto-Conectado (COM)";
        comText.style.color = "#28a745";
        inputEscaner.placeholder = "Escáner activo. Pase la cédula...";
        inputEscaner.style.cursor = "text";

        const decoder = new TextDecoderStream();
        puerto.readable.pipeTo(decoder.writable);
        lector = decoder.readable.getReader();
        escucharLector();
      }
    } catch (err) { }
  }
}

// ==========================================
// 5. LÓGICA DE NEGOCIO (MANUAL Y DESTINO)
// ==========================================
function cargarUnidades() {
  fetch(AppConfig.urlApiUnidades).then(res => res.json()).then(data => {
      selectUnidad.innerHTML = `<option value="">Seleccione ${AppConfig.nomBloque}...</option>`;
      data.forEach(u => selectUnidad.add(new Option(u.nombre, u.id)));
  });
}

selectUnidad.addEventListener("change", function () {
  const unidadId = this.value;
  selectSubunidad.innerHTML = `<option value="">Cargando...</option>`;
  if (!unidadId) { selectSubunidad.innerHTML = `<option value="">Seleccione ${AppConfig.nomBloque} primero</option>`; return; }
  
  fetch(`/api/subunidades/${unidadId}`).then(res => res.json()).then(data => {
      selectSubunidad.innerHTML = `<option value="">Seleccione ${AppConfig.nomUnidad}...</option>`;
      data.forEach(s => selectSubunidad.add(new Option(s.nombre, s.nombre)));
  });
});

document.getElementById("btnModoManual").addEventListener("click", function () {
  esIngresoManual = true; 
  pasoEscaner.style.display = "none"; 
  pasoDatosManuales.style.display = "block"; 
  const docInput = document.getElementById("docManualInput");
  docInput.value = inputEscaner.value.trim();
  docInput.value === "" ? docInput.focus() : document.getElementById("nombreManualInput").focus();
});

document.getElementById("btnContinuarManual").addEventListener("click", function () {
  documentoFinal = document.getElementById("docManualInput").value.trim();
  nombreFinal = document.getElementById("nombreManualInput").value.trim().toUpperCase(); 
  if (documentoFinal === "" || nombreFinal === "") {
    return alert("⚠️ Por favor, completa el documento y el nombre.");
  }
  pasoDatosManuales.style.display = "none";
  pasoApto.style.display = "block";
});

inputEscaner.addEventListener("keydown", function (e) {
  if (e.key === "Enter") {
    e.preventDefault();
    if (inputEscaner.value.trim() !== "") procesarEntradaEscaner(inputEscaner.value);
  }
});


// ==========================================
// 6. EL CEREBRO FINAL (BOTÓN GUARDAR)
// ==========================================
btnGuardar.addEventListener("click", function () {
    if (selectUnidad.value === "" || selectSubunidad.value === "") { 
        return alert(`⚠️ Debes seleccionar ${AppConfig.nomBloque} y ${AppConfig.nomUnidad}.`); 
    }

    btnGuardar.disabled = true;
    btnGuardar.innerText = "⏳ Guardando...";
    infoRegistro.innerHTML = "<b>⌛ Procesando en el servidor...</b>";

    const aptoFinalStr = `${selectUnidad.options[selectUnidad.selectedIndex].text} - ${selectSubunidad.value}`;
    const obsStr = document.getElementById("obsInput").value;

    // --- RUTA A: GUARDAR PAQUETE ---
    if (modoActual === 'paquete') {
        const payloadPaquete = {
            empresa: document.getElementById("empresaPaquete").value,
            repartidor: document.getElementById("repartidorPaquete").value,
            detalle: document.getElementById("detallePaquete").value,
            foto: fotoCapturadaBase64,
            apartamento: aptoFinalStr,
            observaciones: obsStr
        };

        fetch(AppConfig.urlRegistrarPaquete, { 
            method: "POST", 
            headers: { 
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken
            }, 
            body: JSON.stringify(payloadPaquete) 
        })
          .then(res => res.json())
          .then(data => {
            if (data.mensaje === "ok") {
              infoRegistro.innerHTML = `<div style="color: #17a2b8; font-weight: bold; margin-bottom: 5px;">📦 PAQUETE RECIBIDO</div><b>Destino:</b> ${data.apartamento}<br><b>Empresa:</b> ${data.empresa}`;
              reiniciarPantalla();
            } else { 
              infoRegistro.innerHTML = `<div style="color: #dc3545;">❌ Error: ${data.error}</div>`; 
              liberarBotonGuardar();
            }
          }).catch(() => {
              infoRegistro.innerText = "❌ Error crítico de conexión";
              liberarBotonGuardar();
          });

    // --- RUTA B: GUARDAR VISITANTE ---
    } else {
        const vaEnVehiculo = document.getElementById("vehiculoCheck").checked ? 1 : 0;
        const valorPlaca = document.getElementById("placaInput").value.toUpperCase();
        
        if (vaEnVehiculo === 1 && valorPlaca.trim() === "") { 
            liberarBotonGuardar();
            document.getElementById("placaInput").focus(); 
            return alert("⚠️ Por favor ingresa la placa del vehículo."); 
        }

        if (esIngresoManual && (documentoFinal === "" || nombreFinal === "")) {
            reiniciarPantalla();
            return alert("❌ Los datos se perdieron. Reintente.");
        }

        const idTipoDocumento = esIngresoManual ? document.getElementById("tipoDocSelect").value : 1;
        const tipoVisitaStr = document.getElementById("tipoVisitaSelect").value;
        
        const payloadVisitante = {
          es_manual: esIngresoManual, 
          trama: tramaTemporal, 
          documento_manual: documentoFinal, 
          nombre_manual: nombreFinal,      
          tipo_doc_id: idTipoDocumento, 
          tipo_visita: tipoVisitaStr,
          apartamento: aptoFinalStr,
          vehiculo: vaEnVehiculo, 
          placa: valorPlaca,
          observaciones: obsStr,
          acompanantes: parseInt(document.getElementById('acompInput').value) || 0
        };

        fetch(AppConfig.urlRegistrar, { 
            method: "POST", 
            headers: { 
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken
            }, 
            body: JSON.stringify(payloadVisitante) 
        })
          .then(res => res.json())
          .then(data => {
            if (data.mensaje === "ok") {
              const iconoVehiculo = data.vehiculo === 1 ? "🚗" : "🚶";
              infoRegistro.innerHTML = `<div style="color: #28a745; font-weight: bold; margin-bottom: 5px;">✅ REGISTRO EXITOSO</div><b>Destino:</b> ${data.apartamento}<br><b>Visitante:</b> ${data.nombre}<br><b>Transporte:</b> ${iconoVehiculo} ${data.placa || "Peatón"}`;
              reiniciarPantalla();
            } else { 
              infoRegistro.innerHTML = `<div style="color: #dc3545;">❌ Error: ${data.error}</div>`; 
              liberarBotonGuardar();
            }
          }).catch(() => {
              infoRegistro.innerText = "❌ Error crítico de conexión";
              liberarBotonGuardar();
          });
    }
});

// ==========================================
// 7. UTILIDADES (RESET Y EVENTOS EXTRA)
// ==========================================
function liberarBotonGuardar() {
    btnGuardar.disabled = false;
    btnGuardar.innerText = "Finalizar Registro ✅";
}

function reiniciarPantalla() {
  document.getElementById("obsInput").value = ""; 
  selectUnidad.selectedIndex = 0;
  selectSubunidad.innerHTML = `<option value="">Seleccione ${AppConfig.nomBloque} primero</option>`;
  pasoApto.style.display = "none";
  liberarBotonGuardar();

  if (modoActual === 'paquete') {
      document.getElementById("empresaPaquete").value = ""; 
      document.getElementById("repartidorPaquete").value = "";
      document.getElementById("btnRepetirFoto").click(); 
      zonaPaquete.style.display = "block";
  } else {
      esIngresoManual = false;
      documentoFinal = ""; nombreFinal = ""; tramaTemporal = "";
      document.getElementById("docManualInput").value = ""; 
      document.getElementById("nombreManualInput").value = ""; 
      inputEscaner.value = "";
      document.getElementById("vehiculoCheck").checked = false;
      document.getElementById("placaInput").value = ""; 
      document.getElementById("placaInput").style.display = "none";
      document.getElementById('acompInput').value = "0";
      document.getElementById("tipoVisitaSelect").selectedIndex = 0;
      
      pasoDatosManuales.style.display = "none";
      pasoEscaner.style.display = "block";
      setTimeout(() => inputEscaner.focus(), 150);
  }
}

document.getElementById("btnCancelarGlobal").addEventListener("click", reiniciarPantalla);
document.getElementById("btnCancelarManual").addEventListener("click", reiniciarPantalla);

document.getElementById("vehiculoCheck").addEventListener("change", function () {
  const placa = document.getElementById("placaInput");
  placa.style.display = this.checked ? "block" : "none";
  if(this.checked) placa.focus();
});

window.addEventListener('DOMContentLoaded', () => {
    cargarUnidades();
    intentarAutoConexion();
});