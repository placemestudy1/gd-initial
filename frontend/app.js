/**
 * app.js — PlaceMe GD Arena Frontend
 *
 * Uses LiveKit client SDK (CDN) to:
 * 1. Connect to LiveKit room as the user
 * 2. Publish microphone audio
 * 3. Subscribe to and play all agent audio tracks
 * 4. Animate participant bubbles based on audio levels
 * 5. Render live transcript from LiveKit data messages
 * 6. Handle session lifecycle (setup → arena → feedback)
 */

const API_BASE = window.location.origin;

// ─────────────────────────────────────────────────────────────────────────────
// App State
// ─────────────────────────────────────────────────────────────────────────────
const state = {
  room: null,
  token: null,
  wsUrl: null,
  roomName: null,
  topic: null,
  userName: 'You',
  duration: 600,
  timerInterval: null,
  timerRemaining: 600,
  isMuted: false,
  selectedTopic: null,
  customTopic: '',
  transcriptEntries: [],
  audioContexts: {},    // participantId → AudioContext analyzer
  animFrames: {},       // participantId → requestAnimationFrame id
  participantMap: {},   // identity → bubble element
  sessionStarted: false,
  currentPhase: 'opening',
};

// ─────────────────────────────────────────────────────────────────────────────
// GD Topics (fetched from API, also hard-coded as fallback)
// ─────────────────────────────────────────────────────────────────────────────
const FALLBACK_TOPICS = {
  current_affairs: [
    "Is Artificial Intelligence a threat to jobs or a creator of opportunities?",
    "Should India prioritize economic growth over environmental sustainability?",
    "Are social media platforms doing enough to combat misinformation?",
    "Is remote work better for productivity than office work?",
    "Should college education be made free in India?",
  ],
  abstract: [
    "Failure is the stepping stone to success",
    "Does technology make us more or less human?",
    "Is competition healthy or harmful?",
  ],
  business: [
    "Should startups prioritize growth over profitability?",
    "Is corporate social responsibility a genuine commitment or a PR exercise?",
    "Should companies use AI for hiring decisions?",
  ],
  ethics: [
    "Should data privacy be sacrificed for national security?",
    "Is it ethical for companies to collect user data for personalization?",
    "Should there be a universal basic income?",
  ],
};

// Participant config
const PARTICIPANTS = {
  moderator: {
    id: 'moderator',
    name: 'Kavya',
    role: 'Moderator',
    emoji: '🎙️',
    cssClass: 'moderator',
    color: '#a78bfa',
  },
  aarav: {
    id: 'aarav',
    name: 'Aarav',
    role: 'Analytical Debater',
    emoji: '🧠',
    cssClass: 'aarav',
    color: '#f59e0b',
  },
  priya: {
    id: 'priya',
    name: 'Priya',
    role: 'Human-Centered Debater',
    emoji: '💡',
    cssClass: 'priya',
    color: '#34d399',
  },
  user: {
    id: 'user',
    name: 'You',
    role: 'Participant',
    emoji: '🎤',
    cssClass: 'user',
    color: '#3b82f6',
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// DOM Refs
// ─────────────────────────────────────────────────────────────────────────────
let dom = {};

function initDomRefs() {
  dom = {
    screenSetup:    document.getElementById('screen-setup'),
    screenArena:    document.getElementById('screen-arena'),
    screenFeedback: document.getElementById('screen-feedback'),

    // Setup
    topicTabs:      document.getElementById('topic-tabs'),
    topicGrid:      document.getElementById('topic-grid'),
    customTopicInput: document.getElementById('custom-topic-input'),
    userNameInput:  document.getElementById('user-name-input'),
    durationSelect: document.getElementById('duration-select'),
    startBtn:       document.getElementById('start-btn'),

    // Arena
    arenaTopic:     document.getElementById('arena-topic'),
    timerDisplay:   document.getElementById('timer-display'),
    timerText:      document.getElementById('timer-text'),
    timerDot:       document.getElementById('timer-dot'),
    phaseText:      document.getElementById('phase-text'),
    participantsRow: document.getElementById('participants-row'),
    userBubble:     document.getElementById('user-bubble'),
    btnMic:         document.getElementById('btn-mic'),
    btnEnd:         document.getElementById('btn-end'),
    transcriptBody: document.getElementById('transcript-body'),

    // Status overlay
    statusOverlay:  document.getElementById('status-overlay'),
    statusText:     document.getElementById('status-text'),
    statusSubtext:  document.getElementById('status-subtext'),
    statusSteps:    document.getElementById('status-steps'),

    // Feedback
    feedbackTopic:  document.getElementById('feedback-topic'),
    feedbackSpeakTime: document.getElementById('feedback-speak-time'),
    feedbackPoints: document.getElementById('feedback-points'),
    btnNewSession:  document.getElementById('btn-new-session'),
    btnGoHome:      document.getElementById('btn-go-home'),

    // Toast
    toast:          document.getElementById('toast'),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Screen Navigation
// ─────────────────────────────────────────────────────────────────────────────
function showScreen(name) {
  dom.screenSetup?.classList.remove('active');
  dom.screenArena?.classList.remove('active');
  dom.screenFeedback?.classList.remove('active');

  if (name === 'setup')    dom.screenSetup?.classList.add('active');
  if (name === 'arena')    dom.screenArena?.classList.add('active');
  if (name === 'feedback') dom.screenFeedback?.classList.add('active');

  window.scrollTo(0, 0);
}

// ─────────────────────────────────────────────────────────────────────────────
// Status Overlay
// ─────────────────────────────────────────────────────────────────────────────
function showStatus(text, subtext = '', steps = []) {
  if (!dom.statusOverlay) return;
  dom.statusText.textContent = text;
  dom.statusSubtext.textContent = subtext;

  if (dom.statusSteps && steps.length) {
    dom.statusSteps.innerHTML = steps.map((s, i) =>
      `<div class="status-step" id="step-${i}">
        <span class="step-icon">${s.icon || '○'}</span>
        <span>${s.text}</span>
      </div>`
    ).join('');
  }

  dom.statusOverlay?.classList.remove('hidden');
}

function updateStep(index, done = true) {
  const el = document.getElementById(`step-${index}`);
  if (el) {
    el.classList.toggle('done', done);
    el.classList.toggle('active', !done);
    el.querySelector('.step-icon').textContent = done ? '✓' : '⟳';
  }
}

function hideStatus() {
  dom.statusOverlay?.classList.add('hidden');
}

// ─────────────────────────────────────────────────────────────────────────────
// Toast
// ─────────────────────────────────────────────────────────────────────────────
function showToast(msg, duration = 3000) {
  if (!dom.toast) return;
  dom.toast.textContent = msg;
  dom.toast.classList.add('show');
  setTimeout(() => dom.toast.classList.remove('show'), duration);
}

// ─────────────────────────────────────────────────────────────────────────────
// Topic Selection
// ─────────────────────────────────────────────────────────────────────────────
let topicsData = FALLBACK_TOPICS;
let activeCategory = 'current_affairs';

async function loadTopics() {
  try {
    const res = await fetch(`${API_BASE}/api/topics`);
    if (res.ok) {
      const data = await res.json();
      topicsData = data.topics || FALLBACK_TOPICS;
    }
  } catch (e) {
    console.log('Using fallback topics');
  }
  renderTopicTabs();
  renderTopics(activeCategory);
}

function renderTopicTabs() {
  if (!dom.topicTabs) return;
  const categories = Object.keys(topicsData);
  const labels = {
    current_affairs: 'Current Affairs',
    abstract:        'Abstract',
    business:        'Business',
    ethics:          'Ethics',
  };

  dom.topicTabs.innerHTML = categories.map(cat =>
    `<button class="topic-tab ${cat === activeCategory ? 'active' : ''}"
      onclick="switchCategory('${cat}')">${labels[cat] || cat}</button>`
  ).join('');
}

function renderTopics(category) {
  if (!dom.topicGrid) return;
  const topics = topicsData[category] || [];
  dom.topicGrid.innerHTML = topics.map(t =>
    `<button class="topic-pill ${state.selectedTopic === t ? 'selected' : ''}"
      onclick="selectTopic(this, '${t.replace(/'/g, "\\'")}')">${t}</button>`
  ).join('');
}

window.switchCategory = function(cat) {
  activeCategory = cat;
  renderTopicTabs();
  renderTopics(cat);
};

window.selectTopic = function(el, topic) {
  state.selectedTopic = topic;
  state.customTopic = '';
  if (dom.customTopicInput) dom.customTopicInput.value = '';
  document.querySelectorAll('.topic-pill').forEach(p => p.classList.remove('selected'));
  el.classList.add('selected');
};

// ─────────────────────────────────────────────────────────────────────────────
// Start Session
// ─────────────────────────────────────────────────────────────────────────────
async function startSession() {
  const topic = dom.customTopicInput?.value.trim() || state.selectedTopic;
  if (!topic) { showToast('Please select or enter a topic!'); return; }

  const userName = dom.userNameInput?.value.trim() || 'You';
  const duration = parseInt(dom.durationSelect?.value || '600');

  state.topic = topic;
  state.userName = userName;
  state.duration = duration;
  state.timerRemaining = duration;

  // Update user bubble name
  const userNameEl = document.getElementById('user-name-display');
  if (userNameEl) userNameEl.textContent = userName;

  if (dom.startBtn) {
    dom.startBtn.classList.add('loading');
    dom.startBtn.disabled = true;
  }

  showStatus('Setting up your GD Arena...', 'This takes just a moment', [
    { text: 'Creating secure room' },
    { text: 'Joining as ' + userName },
    { text: 'Inviting AI participants' },
    { text: 'Starting discussion' },
  ]);

  try {
    // Step 1: Create session via API
    updateStep(0, false);
    const res = await fetch(`${API_BASE}/api/create-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, user_name: userName, duration }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${res.status}`);
    }

    const sessionData = await res.json();
    state.token   = sessionData.token;
    state.wsUrl   = sessionData.ws_url;
    state.roomName = sessionData.room_name;
    updateStep(0, true);

    // Step 2: Connect to LiveKit room
    updateStep(1, false);
    dom.statusText.textContent = 'Connecting to arena...';
    await connectToRoom(state.token, state.wsUrl);
    updateStep(1, true);

    // Step 3: Wait for agents to join (brief delay)
    updateStep(2, false);
    dom.statusText.textContent = 'AI participants joining...';
    await sleep(2500);
    updateStep(2, true);

    // Step 4: Ready!
    updateStep(3, false);
    dom.statusText.textContent = 'Starting discussion!';
    await sleep(800);
    updateStep(3, true);

    // Switch to arena screen
    if (dom.arenaTopic) dom.arenaTopic.textContent = topic;
    showScreen('arena');
    hideStatus();
    startTimer(duration);

  } catch (err) {
    console.error('Session creation failed:', err);
    hideStatus();
    showToast(`Failed to start: ${err.message}`);
    if (dom.startBtn) {
      dom.startBtn.classList.remove('loading');
      dom.startBtn.disabled = false;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// LiveKit Room Connection
// ─────────────────────────────────────────────────────────────────────────────
async function connectToRoom(token, wsUrl) {
  // LiveKit client is loaded from CDN
  const { Room, RoomEvent, Track, createLocalAudioTrack, ConnectionState, DataPacket_Kind } = window.LivekitClient;

  const room = new Room({
    adaptiveStream: true,
    dynacast: true,
    audioCaptureDefaults: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });

  state.room = room;

  // ── Event: Remote participant connected ──
  room.on(RoomEvent.ParticipantConnected, (participant) => {
    console.log('Participant connected:', participant.identity);
    handleParticipantJoined(participant);
    showToast(`${getDisplayName(participant.identity)} joined the discussion`);
  });

  // ── Event: Remote participant disconnected ──
  room.on(RoomEvent.ParticipantDisconnected, (participant) => {
    console.log('Participant disconnected:', participant.identity);
    markParticipantInactive(participant.identity);
  });

  // ── Event: Track subscribed (agent audio) ──
  room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
    if (track.kind === 'audio') {
      console.log(`Audio track from ${participant.identity}`);
      attachAudioTrack(track, participant);
    }
  });

  // ── Event: Track unsubscribed ──
  room.on(RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
    if (track.kind === 'audio') {
      detachAudioTrack(participant.identity);
    }
  });

  // ── Event: Data received (transcripts + events) ──
  room.on(RoomEvent.DataReceived, (data, participant) => {
    try {
      const msg = JSON.parse(new TextDecoder().decode(data));
      handleDataMessage(msg, participant);
    } catch (e) {
      console.warn('Could not parse data message:', e);
    }
  });

  // ── Event: Active speakers changed ──
  room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
    updateActiveSpeakers(speakers);
  });

  // ── Event: Connection state changed ──
  room.on(RoomEvent.ConnectionStateChanged, (state) => {
    console.log('Connection state:', state);
    if (state === ConnectionState.Disconnected) {
      showToast('Disconnected from arena');
    }
  });

  // Connect to room
  await room.connect(wsUrl, token);
  console.log('Connected to room:', room.name);

  // Publish local microphone
  try {
    await room.localParticipant.setMicrophoneEnabled(true);
    setupLocalAudioVisualizer();
    console.log('Microphone published');
  } catch (e) {
    console.warn('Microphone access failed:', e);
    showToast('Could not access microphone — check browser permissions');
  }

  // Handle already-connected participants (joined before us)
  room.remoteParticipants.forEach((participant) => {
    handleParticipantJoined(participant);
    participant.trackPublications.forEach((pub) => {
      if (pub.track && pub.track.kind === 'audio') {
        attachAudioTrack(pub.track, participant);
      }
    });
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Participant UI Management
// ─────────────────────────────────────────────────────────────────────────────
function getDisplayName(identity) {
  const lower = identity.toLowerCase();
  if (lower.includes('moderator') || lower.includes('kavya')) return 'Kavya (Moderator)';
  if (lower.includes('aarav')) return 'Aarav';
  if (lower.includes('priya')) return 'Priya';
  return identity;
}

function getParticipantCss(identity) {
  const lower = identity.toLowerCase();
  if (lower.includes('moderator') || lower.includes('kavya')) return 'moderator';
  if (lower.includes('aarav')) return 'aarav';
  if (lower.includes('priya')) return 'priya';
  return 'user';
}

function handleParticipantJoined(participant) {
  const css = getParticipantCss(participant.identity);
  const bubble = document.getElementById(`bubble-${css}`);
  if (bubble) {
    bubble.classList.remove('inactive');
    state.participantMap[participant.identity] = bubble;
  }
}

function markParticipantInactive(identity) {
  const css = getParticipantCss(identity);
  const bubble = document.getElementById(`bubble-${css}`);
  if (bubble) bubble.classList.add('inactive');
}

// ─────────────────────────────────────────────────────────────────────────────
// Audio Playback & Visualization
// ─────────────────────────────────────────────────────────────────────────────
function attachAudioTrack(track, participant) {
  const identity = participant.identity;

  // Create audio element and attach track
  const audioEl = track.attach();
  audioEl.id = `audio-${identity}`;
  audioEl.autoplay = true;
  audioEl.style.display = 'none';
  document.body.appendChild(audioEl);

  // Set up Web Audio API analyzer for visualization
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source   = audioCtx.createMediaElementSource(audioEl);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 64;
    analyser.smoothingTimeConstant = 0.7;
    source.connect(analyser);
    analyser.connect(audioCtx.destination);

    state.audioContexts[identity] = { audioCtx, analyser, audioEl };
    startVisualization(identity, analyser);
  } catch (e) {
    console.warn('Audio visualization setup failed:', e);
  }
}

function detachAudioTrack(identity) {
  const el = document.getElementById(`audio-${identity}`);
  if (el) el.remove();

  if (state.audioContexts[identity]) {
    try { state.audioContexts[identity].audioCtx.close(); } catch (e) {}
    delete state.audioContexts[identity];
  }

  if (state.animFrames[identity]) {
    cancelAnimationFrame(state.animFrames[identity]);
    delete state.animFrames[identity];
  }

  const css = getParticipantCss(identity);
  const bubble = document.getElementById(`bubble-${css}`);
  if (bubble) bubble.classList.remove('speaking');
}

function startVisualization(identity, analyser) {
  const dataArray = new Uint8Array(analyser.frequencyBinCount);
  const css = getParticipantCss(identity);
  const bubble = document.getElementById(`bubble-${css}`);
  const bars = bubble?.querySelectorAll('.audio-bar');

  function tick() {
    analyser.getByteFrequencyData(dataArray);

    // Calculate RMS volume
    const rms = Math.sqrt(dataArray.reduce((sum, v) => sum + v * v, 0) / dataArray.length);
    const isSpeaking = rms > 8;

    // Update speaking class
    if (bubble) {
      bubble.classList.toggle('speaking', isSpeaking);
    }

    // Animate bars
    if (bars && isSpeaking) {
      bars.forEach((bar, i) => {
        const val = dataArray[i * 2] || 0;
        const h = Math.max(4, (val / 255) * 20);
        bar.style.height = `${h}px`;
      });
    } else if (bars) {
      bars.forEach(bar => { bar.style.height = '4px'; });
    }

    state.animFrames[identity] = requestAnimationFrame(tick);
  }

  state.animFrames[identity] = requestAnimationFrame(tick);
}

function setupLocalAudioVisualizer() {
  // Visualize user's own microphone
  if (!state.room?.localParticipant) return;

  const audioTracks = Array.from(state.room.localParticipant.trackPublications.values())
    .filter(pub => pub.track?.kind === 'audio');

  if (!audioTracks.length) return;

  const track = audioTracks[0].track;
  const mediaStreamTrack = track.mediaStreamTrack;
  const stream = new MediaStream([mediaStreamTrack]);

  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source   = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 64;
    analyser.smoothingTimeConstant = 0.7;
    source.connect(analyser);

    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    const bubble = document.getElementById('bubble-user');
    const bars = bubble?.querySelectorAll('.audio-bar');

    function tick() {
      analyser.getByteFrequencyData(dataArray);
      const rms = Math.sqrt(dataArray.reduce((sum, v) => sum + v * v, 0) / dataArray.length);
      const isSpeaking = rms > 10 && !state.isMuted;

      if (bubble) bubble.classList.toggle('speaking', isSpeaking);
      if (bars && isSpeaking) {
        bars.forEach((bar, i) => {
          const val = dataArray[i * 2] || 0;
          bar.style.height = `${Math.max(4, (val / 255) * 20)}px`;
        });
      } else if (bars) {
        bars.forEach(bar => { bar.style.height = '4px'; });
      }

      requestAnimationFrame(tick);
    }
    tick();
  } catch (e) {
    console.warn('Local visualizer failed:', e);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Active Speakers
// ─────────────────────────────────────────────────────────────────────────────
function updateActiveSpeakers(speakers) {
  // Remove speaking class from all non-user bubbles first
  ['moderator', 'aarav', 'priya'].forEach(css => {
    const b = document.getElementById(`bubble-${css}`);
    if (b && !speakers.find(s => getParticipantCss(s.identity) === css)) {
      // Only remove if not detected by audio analyzer
      // Audio analyzer takes priority — don't remove here if analyzer is active
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Data Messages (transcripts + events from agents)
// ─────────────────────────────────────────────────────────────────────────────
function handleDataMessage(msg, participant) {
  switch (msg.event) {
    case 'transcript':
      addTranscriptEntry(msg.speaker, msg.text, msg.role);
      if (msg.speak) {
        speakText(msg.text, msg.role);
      }
      break;

    case 'timer_tick':
      if (msg.remaining !== undefined) {
        state.timerRemaining = msg.remaining;
        updateTimerDisplay(msg.remaining);
      }
      break;

    case 'topic_set':
      if (dom.arenaTopic && msg.topic) dom.arenaTopic.textContent = msg.topic;
      break;

    case 'session_ended':
      endSession();
      break;

    case 'phase_change':
      if (dom.phaseText && msg.phase) {
        dom.phaseText.textContent = formatPhase(msg.phase);
        state.currentPhase = msg.phase;
      }
      break;
  }
}

function formatPhase(phase) {
  const labels = {
    opening: '🟢 Opening',
    main_discussion: '🔵 Main Discussion',
    rebuttal: '🟠 Rebuttal',
    closing: '🔴 Closing',
  };
  return labels[phase] || phase;
}

function speakText(text, role) {
  if (!window.speechSynthesis) return;
  
  const utterance = new SpeechSynthesisUtterance(text);
  const voices = window.speechSynthesis.getVoices();
  
  if (role.includes('moderator')) {
    utterance.voice = voices.find(v => v.name.includes('Female') || v.name.includes('Zira') || v.name.includes('Samantha') || v.name.includes('Victoria')) || voices[0];
    utterance.pitch = 1.1;
    utterance.rate = 1.05;
  } else if (role.includes('aarav')) {
    utterance.voice = voices.find(v => v.name.includes('Male') || v.name.includes('David') || v.name.includes('Alex') || v.name.includes('Daniel')) || voices[0];
    utterance.pitch = 0.9;
    utterance.rate = 1.05;
  } else if (role.includes('priya')) {
    utterance.voice = voices.find(v => v.name.includes('Female') || v.name.includes('Hazel') || v.name.includes('Karen') || v.name.includes('Fiona')) || voices[0];
    utterance.pitch = 1.2;
    utterance.rate = 1.0;
  }
  
  window.speechSynthesis.speak(utterance);
}

// ─────────────────────────────────────────────────────────────────────────────
// Transcript
// ─────────────────────────────────────────────────────────────────────────────
function addTranscriptEntry(speaker, text, role) {
  if (!dom.transcriptBody) return;
  if (!text?.trim()) return;

  const entry = document.createElement('div');
  entry.className = `transcript-entry ${role}`;
  entry.innerHTML = `
    <div class="entry-speaker">${speaker}</div>
    <div class="entry-text">${escapeHtml(text)}</div>
  `;
  dom.transcriptBody.appendChild(entry);

  // Auto-scroll to bottom
  dom.transcriptBody.scrollTop = dom.transcriptBody.scrollHeight;

  state.transcriptEntries.push({ speaker, text, role });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

// ─────────────────────────────────────────────────────────────────────────────
// Timer
// ─────────────────────────────────────────────────────────────────────────────
function startTimer(duration) {
  state.timerRemaining = duration;
  clearInterval(state.timerInterval);

  state.timerInterval = setInterval(() => {
    state.timerRemaining--;
    updateTimerDisplay(state.timerRemaining);
    if (state.timerRemaining <= 0) {
      clearInterval(state.timerInterval);
      endSession();
    }
  }, 1000);

  updateTimerDisplay(duration);
}

function updateTimerDisplay(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  const text = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

  if (dom.timerText) dom.timerText.textContent = text;

  if (dom.timerDisplay) {
    dom.timerDisplay.classList.remove('warning', 'critical');
    if (seconds <= 30) dom.timerDisplay.classList.add('critical');
    else if (seconds <= 120) dom.timerDisplay.classList.add('warning');
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Mic Toggle
// ─────────────────────────────────────────────────────────────────────────────
async function toggleMic() {
  if (!state.room?.localParticipant) return;

  state.isMuted = !state.isMuted;
  await state.room.localParticipant.setMicrophoneEnabled(!state.isMuted);

  if (dom.btnMic) {
    dom.btnMic.classList.toggle('muted', state.isMuted);
    dom.btnMic.title = state.isMuted ? 'Unmute' : 'Mute';
    dom.btnMic.querySelector('span').textContent = state.isMuted ? '🔇' : '🎤';
  }

  showToast(state.isMuted ? 'Microphone muted' : 'Microphone active');
}

// ─────────────────────────────────────────────────────────────────────────────
// End Session
// ─────────────────────────────────────────────────────────────────────────────
function endSession() {
  clearInterval(state.timerInterval);

  // Disconnect from room
  if (state.room) {
    state.room.disconnect();
    state.room = null;
  }

  // Clean up audio
  Object.values(state.audioContexts).forEach(({ audioCtx }) => {
    try { audioCtx.close(); } catch (e) {}
  });
  state.audioContexts = {};

  Object.values(state.animFrames).forEach(id => cancelAnimationFrame(id));
  state.animFrames = {};

  // Remove audio elements
  document.querySelectorAll('[id^="audio-"]').forEach(el => el.remove());

  // Calculate stats
  const totalTime = state.duration - state.timerRemaining;
  const speakTime = Math.round(totalTime * 0.3); // Estimate
  const points = state.transcriptEntries.filter(e => e.role === 'user').length;

  // Show feedback
  showFeedback(speakTime, points);
}

function showFeedback(speakSeconds, points) {
  const mins = Math.floor(speakSeconds / 60);
  const secs = speakSeconds % 60;

  if (dom.feedbackTopic) dom.feedbackTopic.textContent = state.topic;
  if (dom.feedbackSpeakTime) dom.feedbackSpeakTime.textContent = `${mins}m ${secs}s`;
  if (dom.feedbackPoints) dom.feedbackPoints.textContent = points || '—';

  showScreen('feedback');
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────
function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

// ─────────────────────────────────────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initDomRefs();

  // Wire up buttons
  dom.startBtn?.addEventListener('click', startSession);
  dom.btnMic?.addEventListener('click', toggleMic);
  dom.btnEnd?.addEventListener('click', () => {
    if (confirm('End this session? Your progress will be saved.')) endSession();
  });
  dom.btnNewSession?.addEventListener('click', () => {
    showScreen('setup');
    // Reset state
    state.selectedTopic = null;
    state.transcriptEntries = [];
    document.querySelectorAll('.topic-pill').forEach(p => p.classList.remove('selected'));
    if (dom.startBtn) {
      dom.startBtn.classList.remove('loading');
      dom.startBtn.disabled = false;
    }
  });
  dom.btnGoHome?.addEventListener('click', () => { window.location.href = '/'; });

  // Custom topic clears selection
  dom.customTopicInput?.addEventListener('input', (e) => {
    state.customTopic = e.target.value;
    if (e.target.value.trim()) {
      state.selectedTopic = null;
      document.querySelectorAll('.topic-pill').forEach(p => p.classList.remove('selected'));
    }
  });

  // Load topics from API
  await loadTopics();

  // Show setup screen
  showScreen('setup');
  hideStatus();
});
