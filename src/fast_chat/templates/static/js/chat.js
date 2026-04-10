const STORAGE_KEY_SELECTED_USER = 'selectedUserId';

let selectedUserId = null;
let socket = null;



const API = {
  base: () => window.location.href,

  async getConversations() {
    const r = await fetch(`${this.base()}v1/conversations/`);
    return r.json();
  },

  async addConversation(partnerId) {
    const r = await fetch(`${this.base()}v1/conversations/${partnerId}`, {
      method: 'POST',
    });
    return r.json();
  },

  async deleteConversation(partnerId) {
    const r = await fetch(`${this.base()}v1/conversations/${partnerId}`, {
      method: 'DELETE',
    });
    return r.ok;
  },

  async searchAvailableUsers(query = '') {
    const qs = query ? `?q=${encodeURIComponent(query)}` : '';
    const r = await fetch(`${this.base()}v1/conversations/search${qs}`);
    return r.json();
  },

  async getMessages(userId) {
    const r = await fetch(`${this.base()}v1/messages/${userId}`);
    return r.json();
  },
};


class ChatApp {

  constructor() {
    this.conversations = [];
    this.currentChat = null;
    this.init();
  }

  async init() {
    await this.loadConversations();
    this.setupEventListeners();
    this.restoreSelectedChat();
    document.getElementById('close-chat-btn').addEventListener('click', () => this.closeChat());
  }

  async loadConversations() {
    this.conversations = await API.getConversations();
    this.renderConversations();
  }

  renderConversations() {
    const list = document.getElementById('messages-list');
    if (!this.conversations.length) {
      list.innerHTML = '<div class="messages-empty">Нет чатов. Нажмите + чтобы найти пользователя.</div>';
      return;
    }
    list.innerHTML = this.conversations.map(user => this._userItemHtml(user)).join('');

    list.querySelectorAll('.user-item').forEach(item => {
      item.addEventListener('click', (e) => {
        if (e.target.closest('.remove-chat-btn')) return;
        this.selectUser(item.dataset.userId);
      });
    });

    list.querySelectorAll('.remove-chat-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.removeConversation(parseInt(btn.dataset.partnerId));
      });
    });

    this.highlightActiveUser();
  }

  _userItemHtml(user) {
    return `
      <div class="user-item" data-user-id="${user.id}">
        <div class="user-avatar">${user.full_name[0].toUpperCase()}</div>
        <span class="user-name">${user.full_name}</span>
        <button class="remove-chat-btn" data-partner-id="${user.id}" title="Удалить чат">✕</button>
      </div>
    `;
  }

  async removeConversation(partnerId) {
    const ok = await API.deleteConversation(partnerId);
    if (!ok) {
      showToast('Не удалось удалить чат', 'error');
      return;
    }
    if (selectedUserId && parseInt(selectedUserId) === partnerId) {
      this.closeChat();
    }
    this.conversations = this.conversations.filter(u => u.id !== partnerId);
    this.renderConversations();
  }


  setupEventListeners() {
    const dmAddBtn      = document.getElementById('dm-add-btn');
    const searchOverlay = document.getElementById('search-modal-overlay');
    const searchInput   = document.getElementById('search-input');

    dmAddBtn.addEventListener('click', async () => {
      searchOverlay.classList.add('open');
      searchInput.value = '';
      const users = await API.searchAvailableUsers();
      this.renderSearchResults(users);
      searchInput.focus();
    });

    searchOverlay.addEventListener('click', (e) => {
      if (e.target === searchOverlay) searchOverlay.classList.remove('open');
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') searchOverlay.classList.remove('open');
    });

    searchInput.addEventListener('input', async (e) => {
      const users = await API.searchAvailableUsers(e.target.value);
      this.renderSearchResults(users);
    });

    const sendButton   = document.getElementById('submit');
    const chatTextarea = document.getElementById('chat-textarea');

    sendButton.addEventListener('click', () => this.sendMessage());
    chatTextarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    document.querySelectorAll('.toolbar-btn[data-action]').forEach(btn => {
      btn.addEventListener('click', () => this.applyFormat(btn.dataset.action));
    });

    chatTextarea.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key === 'b') { e.preventDefault(); this.applyFormat('bold'); }
      if (e.ctrlKey && e.key === 'i') { e.preventDefault(); this.applyFormat('italic'); }
    });

    const emojiToggle = document.getElementById('emoji-toggle');
    const emojiPicker = document.getElementById('emoji-picker');
    const emojiSearch = document.getElementById('emoji-search');

    emojiToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = emojiPicker.classList.toggle('open');
      if (isOpen) {
        this.renderEmojiPicker(EMOJI_DATA);
        emojiSearch.value = '';
        emojiSearch.focus();
      }
    });

    emojiSearch.addEventListener('input', () => {
      const q = emojiSearch.value.toLowerCase();
      if (!q) { this.renderEmojiPicker(EMOJI_DATA); return; }
      const results = EMOJI_DATA.map(cat => ({
        name: cat.name,
        emojis: cat.emojis.filter(e => e.k.some(k => k.includes(q))),
      })).filter(cat => cat.emojis.length);
      this.renderEmojiPicker(results);
    });

    document.addEventListener('click', (e) => {
      if (!emojiPicker.contains(e.target) && e.target !== emojiToggle) {
        emojiPicker.classList.remove('open');
      }
    });
  }

  renderSearchResults(users) {
    const container = document.getElementById('search-modal-results');
    if (!users.length) {
      container.innerHTML = '<div style="color:#72767d;font-size:0.85rem;padding:0.5rem">Пользователи не найдены</div>';
      return;
    }
    container.innerHTML = users.map(user => `
      <div class="user-item" data-user-id="${user.id}">
        <div class="user-avatar">${user.full_name[0].toUpperCase()}</div>
        <span class="user-name">${user.full_name}</span>
      </div>
    `).join('');

    container.querySelectorAll('.user-item').forEach(item => {
      item.addEventListener('click', () => this.addConversationFromSearch(item.dataset.userId));
    });
  }

  async addConversationFromSearch(userId) {
    document.getElementById('search-modal-overlay').classList.remove('open');

    await API.addConversation(userId);
    await this.loadConversations();
    this.selectUser(userId);
  }


  restoreSelectedChat() {
    const savedUserId = localStorage.getItem(STORAGE_KEY_SELECTED_USER);
    if (savedUserId && this.conversations.find(u => u.id === parseInt(savedUserId))) {
      this.selectUser(savedUserId);
    }
  }

  highlightActiveUser() {
    document.querySelectorAll('#messages-list .user-item').forEach(item => {
      item.classList.toggle('active', item.dataset.userId === String(selectedUserId));
    });
  }

  showChatArea() {
    document.getElementById('no-chat-placeholder').style.display = 'none';
    document.getElementById('chat-header').style.display = '';
    document.getElementById('chat-messages').style.display = '';
    document.getElementById('chat-input').style.display = '';
  }

  hideChatArea() {
    document.getElementById('no-chat-placeholder').style.display = '';
    document.getElementById('chat-header').style.display = 'none';
    document.getElementById('chat-messages').style.display = 'none';
    document.getElementById('chat-input').style.display = 'none';
  }

  closeChat() {
    if (socket && socket.readyState !== WebSocket.CLOSED) {
      socket.close();
    }
    selectedUserId = null;
    this.currentChat = null;
    localStorage.removeItem(STORAGE_KEY_SELECTED_USER);
    this.clearMessages();
    this.hideChatArea();
    this.highlightActiveUser();
  }

  async selectUser(userId) {
    this.currentChat = this.conversations.find(u => u.id === parseInt(userId));
    if (!this.currentChat) return;

    selectedUserId = userId;
    localStorage.setItem(STORAGE_KEY_SELECTED_USER, userId);

    document.querySelector('.current-chat-name').textContent = this.currentChat.full_name;
    this.clearMessages();
    this.showChatArea();
    this.highlightActiveUser();

    await this.connectWebSocket();
    await this.loadMessages(userId);
  }

  async sendMessage() {
    const messageInput = document.getElementById('chat-textarea');
    const message = messageInput.value.trim();
    const currentUser = document.getElementById('my_account').getAttribute('data-user-id');

    if (message && selectedUserId) {
      const payload = { recipient_id: selectedUserId, body: message, sender_id: currentUser };
      try {
        socket.send(JSON.stringify(payload));
        messageInput.value = '';
      } catch (error) {
        console.error('Ошибка при отправке сообщения:', error);
      }
    }
  }

  async addMessage(message) {
    const chatMessages = document.getElementById('chat-messages');
    const messageElement = document.createElement('div');
    const currentUser = document.getElementById('my_account').getAttribute('data-user-id');

    let avatarName = '';
    if (parseInt(message.content.sender_id) === parseInt(currentUser)) {
      messageElement.className = 'message sent';
      avatarName = 'You';
    } else {
      messageElement.className = 'message';
      avatarName = this.currentChat.full_name[0].toUpperCase();
    }

    const safeHtml = marked.parse(message.content.body ?? '');
    messageElement.innerHTML = `
      <div class="user-avatar">${avatarName}</div>
      <div class="message-content">
        <div class="message-text">${safeHtml}</div>
      </div>
    `;

    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  async loadMessages(userId) {
    try {
      const messages = await API.getMessages(userId);
      for (const message of messages) {
        await this.addMessage({ content: message });
      }
    } catch (error) {
      console.error('Ошибка загрузки сообщений:', error);
    }
  }

  async connectWebSocket() {
    if (socket && socket.readyState !== WebSocket.CLOSED) {
      socket.close();
    }

    const currentUser = document.getElementById('my_account').getAttribute('data-user-id');
    socket = new WebSocket(`ws://${window.location.host}/v1/ws/${currentUser}`);

    socket.onopen = () => console.log('WebSocket соединение открыто.');

    socket.onmessage = (event) => {
      const incomingMessage = JSON.parse(event.data);
      if (
        parseInt(incomingMessage.sender_id) === parseInt(selectedUserId) ||
        parseInt(incomingMessage.recipient_id) === parseInt(selectedUserId)
      ) {
        this.addMessage({ content: incomingMessage });
      }
    };

    socket.onclose = () => console.log('WebSocket соединение закрыто.');
  }

  clearMessages() {
    document.getElementById('chat-messages').innerHTML = '';
  }


  applyFormat(action) {
    const ta = document.getElementById('chat-textarea');
    const start = ta.selectionStart;
    const end   = ta.selectionEnd;
    const sel   = ta.value.slice(start, end);

    const FORMATS = {
      bold:      { wrap: ['**', '**'],       placeholder: 'жирный текст' },
      italic:    { wrap: ['_', '_'],         placeholder: 'курсивный текст' },
      strike:    { wrap: ['~~', '~~'],       placeholder: 'зачеркнутый текст' },
      code:      { wrap: ['`', '`'],         placeholder: 'код' },
      codeblock: { wrap: ['```\n', '\n```'], placeholder: 'код' },
      quote:     { wrap: ['> ', ''],         placeholder: 'цитата' },
      link:      { wrap: ['[', '](url)'],    placeholder: 'текст ссылки' },
    };

    const fmt = FORMATS[action];
    if (!fmt) return;

    const [before, after] = fmt.wrap;
    const inner = sel || fmt.placeholder;
    const replacement = before + inner + after;

    ta.focus();
    document.execCommand('insertText', false, replacement);

    const newStart = start + before.length;
    const newEnd   = newStart + inner.length;
    ta.setSelectionRange(newStart, newEnd);
  }


  renderEmojiPicker(data) {
    const body = document.getElementById('emoji-body');
    if (!data.length) {
      body.innerHTML = '<div style="color:#72767d;font-size:0.85rem;padding:0.25rem 0.5rem">Nothing found</div>';
      return;
    }
    body.innerHTML = data.map(cat =>
      `<div>
        <div class="emoji-category-title">${cat.name}</div>
        <div class="emoji-grid">${cat.emojis.map(e =>
          `<button class="emoji-item" title="${e.k[0]}">${e.e}</button>`
        ).join('')}</div>
      </div>`
    ).join('');

    body.querySelectorAll('.emoji-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const ta = document.getElementById('chat-textarea');
        const s = ta.selectionStart, end = ta.selectionEnd;
        ta.value = ta.value.slice(0, s) + btn.textContent + ta.value.slice(end);
        const pos = s + btn.textContent.length;
        ta.setSelectionRange(pos, pos);
        ta.focus();
        document.getElementById('emoji-picker').classList.remove('open');
      });
    });
  }
}


document.addEventListener('DOMContentLoaded', () => {
  new ChatApp();
});

document.getElementById('logout-button').addEventListener('click', async () => {
  try {
    const response = await fetch(`${window.location.href}v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });

    if (response.ok) {
      localStorage.removeItem(STORAGE_KEY_SELECTED_USER);
      document.cookie = 'session_cookie=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
      showToast('Вы успешно вышли из аккаунта', 'success');
      setTimeout(() => { window.location.href = `${window.location.href}`; }, 1200);
    } else {
      showToast('Не удалось выйти. Попробуйте ещё раз.', 'error');
    }
  } catch (error) {
    console.error('Error during logout:', error);
    showToast('Произошла ошибка при выходе. Попробуйте ещё раз.', 'error');
  }
});
