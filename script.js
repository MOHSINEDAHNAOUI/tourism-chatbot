// ─────────────────────────────
// Init
// ─────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initChat();
});

// ─────────────────────────────
// State — keeps the full conversation history
// ─────────────────────────────
let chatOpen   = false;
let chatHistory = [];   // [{ user: "...", bot: "..." }, ...]

// ─────────────────────────────
// Toggle chat panel
// ─────────────────────────────
function toggleChat() {
  chatOpen = !chatOpen;
  const panel = document.getElementById('chat-panel');
  const icon  = document.getElementById('concierge-icon');

  if (chatOpen) {
    panel.classList.remove('hidden');
    panel.classList.add('flex', 'animate-slideUp');
    icon.textContent = '✕';
    setTimeout(() => document.getElementById('chat-input').focus(), 300);
    scrollMessages();
  } else {
    panel.classList.add('hidden');
    panel.classList.remove('flex', 'animate-slideUp');
    icon.textContent = '💬';
  }
}

// ─────────────────────────────
// Welcome message
// ─────────────────────────────
function initChat() {
  addMessage('bot',
    "Bonjour et bienvenue au **Grand Palais Hotel** ! 🌟\n" +
    "Je suis votre concierge IA. Je peux vous renseigner sur :\n" +
    "• Les villes & attractions du Maroc 🗺️\n" +
    "• Nos hôtels & riads 🏨\n" +
    "• Les réservations & tarifs 💳\n\n" +
    "Comment puis-je vous aider ?"
  );
}

// ─────────────────────────────
// Send message
// ─────────────────────────────
function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChat();
  }
}

async function sendChat() {
  const input   = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const msg     = input.value.trim();
  if (!msg) return;

  input.value      = '';
  input.disabled   = true;
  sendBtn.disabled = true;

  addMessage('user', msg);
  const typingId = addTyping();

  try {
    const res = await fetch('/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        message: msg,
        history: chatHistory          // ← send full conversation history
      }),
    });

    const data = await res.json();
    removeTyping(typingId);

    const reply = data.reply || "Je suis navré, une erreur s'est produite.";
    addMessage('bot', reply);

    // Save this turn to history
    chatHistory.push({ user: msg, bot: reply });

  } catch {
    removeTyping(typingId);
    addMessage('bot', "Désolé, le concierge est momentanément indisponible. Veuillez réessayer.");
  }

  input.disabled   = false;
  sendBtn.disabled = false;
  input.focus();
}

// ─────────────────────────────
// Message helpers
// ─────────────────────────────
function addMessage(role, text) {
  const msgs = document.getElementById('messages');
  const div  = document.createElement('div');

  const base = 'max-w-[84%] px-3.5 py-2.5 rounded-2xl text-[13.5px] leading-snug';
  const bot  = 'self-start bg-white border border-black/10 text-[#1D1D1F] shadow-sm rounded-bl-sm animate-fadeUp';
  const user = 'self-end bg-[#1D1D1F] text-white rounded-br-sm animate-fadeUp';

  div.className = `${base} ${role === 'bot' ? bot : user}`;
  div.innerHTML = formatText(text);
  msgs.appendChild(div);
  scrollMessages();
}

function addTyping() {
  const msgs = document.getElementById('messages');
  const id   = 'typing-' + Date.now();
  const div  = document.createElement('div');
  div.id        = id;
  div.className = 'self-start flex items-center gap-1 bg-white border border-black/10 px-4 py-3.5 rounded-2xl rounded-bl-sm shadow-sm';
  div.innerHTML = `
    <span class="w-1.5 h-1.5 rounded-full bg-[#86868B] dot1"></span>
    <span class="w-1.5 h-1.5 rounded-full bg-[#86868B] dot2"></span>
    <span class="w-1.5 h-1.5 rounded-full bg-[#86868B] dot3"></span>
  `;
  msgs.appendChild(div);
  scrollMessages();
  return id;
}

function removeTyping(id) {
  document.getElementById(id)?.remove();
}

// Basic markdown: bold, line breaks, bullet points
function formatText(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^•\s(.+)$/gm, '<span class="block pl-2 before:content-[\'•\'] before:mr-1.5 before:text-[#86868B]">$1</span>')
    .replace(/\n/g, '<br/>');
}

function scrollMessages() {
  const msgs = document.getElementById('messages');
  setTimeout(() => { msgs.scrollTop = msgs.scrollHeight; }, 50);
}
