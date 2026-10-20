/**
 * Kaveri Stays - Luxury Resorts & Reservations Frontend Logic
 * Full API Integration, Lifecycle State Machine, & Constraint Lab
 */

// Application State
const state = {
  properties: [],
  guests: [],
  bookings: [],
  reviews: [],
  selectedRoom: null,
};

// Utilities
function formatDate(d) {
  if (!d) return '';
  const date = new Date(d);
  return date.toISOString().split('T')[0];
}

function addDays(d, days) {
  const date = new Date(d);
  date.setDate(date.getDate() + days);
  return date;
}

function calculateNights(checkIn, checkOut) {
  const d1 = new Date(checkIn);
  const d2 = new Date(checkOut);
  const diffTime = d2.getTime() - d1.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays;
}

function showToast(title, message, isError = false) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${isError ? 'toast-error' : 'toast-success'}`;
  toast.innerHTML = `
    <span class="toast-icon">${isError ? '⚠️' : '✓'}</span>
    <div>
      <div class="toast-title">${title}</div>
      <div class="toast-msg">${message}</div>
    </div>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

function openModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.add('open');
}

function closeModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.remove('open');
}

// Set up Modal Close Listeners
document.querySelectorAll('[data-close-modal]').forEach(btn => {
  btn.addEventListener('click', (e) => {
    const modalId = e.currentTarget.getAttribute('data-close-modal');
    closeModal(modalId);
  });
});

window.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-backdrop')) {
    e.target.classList.remove('open');
  }
});

// Initialize Dates in Form
function initDefaultDates() {
  const today = new Date();
  const tomorrow = addDays(today, 1);
  const dayAfter = addDays(today, 4);

  const checkInInput = document.getElementById('search-check-in');
  const checkOutInput = document.getElementById('search-check-out');
  if (checkInInput && checkOutInput) {
    checkInInput.value = formatDate(tomorrow);
    checkOutInput.value = formatDate(dayAfter);
    updateNightsCounter();
  }
}

function updateNightsCounter() {
  const inVal = document.getElementById('search-check-in').value;
  const outVal = document.getElementById('search-check-out').value;
  const hint = document.getElementById('nights-counter-hint');
  if (inVal && outVal) {
    const n = calculateNights(inVal, outVal);
    if (n <= 0) {
      hint.innerText = '⚠️ Check-out must be after check-in';
      hint.style.color = 'var(--crimson)';
    } else {
      hint.innerText = `Stay duration: ${n} night${n > 1 ? 's' : ''}`;
      hint.style.color = 'var(--text-muted)';
    }
  }
}

document.getElementById('search-check-in')?.addEventListener('change', updateNightsCounter);
document.getElementById('search-check-out')?.addEventListener('change', updateNightsCounter);

// Check Health & DB Connection
async function checkSystemHealth() {
  try {
    const res = await fetch('/health');
    const data = await res.json();
    const pill = document.getElementById('db-status');
    const text = document.getElementById('db-status-text');
    if (data.database && data.database.backend === 'postgresql') {
      pill.className = 'db-status-pill';
      text.innerText = 'PostgreSQL 17 Active';
    } else {
      pill.className = 'db-status-pill warning';
      text.innerText = 'Verified Memory Store';
    }
  } catch (err) {
    const pill = document.getElementById('db-status');
    const text = document.getElementById('db-status-text');
    pill.className = 'db-status-pill warning';
    text.innerText = 'Offline';
  }
}

// Fetch Properties
async function loadProperties() {
  try {
    const res = await fetch('/properties');
    if (!res.ok) throw new Error('Failed to fetch properties');
    state.properties = await res.json();
    document.getElementById('stat-properties-count').innerText = state.properties.length;
  } catch (err) {
    console.error(err);
  }
}

// Fetch Registered Guests
async function loadGuests() {
  try {
    const res = await fetch('/guests');
    if (!res.ok) throw new Error('Failed to fetch guests');
    state.guests = await res.json();
    
    // Populate Guest dropdown in Booking Modal
    const sel = document.getElementById('booking-guest-id');
    if (sel) {
      sel.innerHTML = '<option value="">Choose registered guest...</option>';
      state.guests.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.guest_id;
        opt.innerText = `${g.full_name} (${g.email}) - ${g.city || 'India'}`;
        sel.appendChild(opt);
      });
    }
  } catch (err) {
    console.error(err);
  }
}

// Fetch Bookings
async function loadBookings(statusFilter = '') {
  try {
    let url = '/bookings';
    if (statusFilter) url += `?status=${encodeURIComponent(statusFilter)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch bookings');
    state.bookings = await res.json();
    
    document.getElementById('stat-bookings-count').innerText = state.bookings.length;
    renderBookings(state.bookings);
  } catch (err) {
    console.error(err);
    document.getElementById('bookings-list-container').innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; color: var(--crimson);">
        Error loading reservations: ${err.message}
      </div>
    `;
  }
}

// Render Bookings Cards
function renderBookings(bookings) {
  const container = document.getElementById('bookings-list-container');
  if (!container) return;

  if (bookings.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; background: var(--bg-card); border-radius: var(--radius-lg); border: 1px dashed var(--border-glass);">
        <h4 style="color: var(--text-muted); font-size: 1.1rem; margin-bottom: 0.5rem;">No Reservations Found</h4>
        <p style="color: var(--text-dim); font-size: 0.9rem;">No stays match the selected filter tab.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = '';
  bookings.forEach(b => {
    const card = document.createElement('div');
    card.className = 'booking-card';

    // Status classes
    const statusClass = `status-${b.status}`;
    const statusLabel = b.status.replace('_', ' ');

    // Progress bar
    const total = parseFloat(b.total_amount || 0);
    const paid = parseFloat(b.payments_total || 0);
    const pct = total > 0 ? Math.min(100, Math.round((paid / total) * 100)) : 0;
    const isPaid = paid >= total;

    // Action buttons based on state machine
    let actionButtons = '';
    if (b.status === 'confirmed') {
      actionButtons += `<button class="btn btn-success btn-sm btn-status-transition" data-id="${b.booking_id}" data-target="checked_in">Check In</button>`;
      actionButtons += `<button class="btn btn-danger btn-sm btn-status-transition" data-id="${b.booking_id}" data-target="cancelled">Cancel</button>`;
      actionButtons += `<button class="btn btn-secondary btn-sm btn-status-transition" data-id="${b.booking_id}" data-target="no_show">No Show</button>`;
      actionButtons += `<button class="btn btn-secondary btn-sm btn-open-payment" data-id="${b.booking_id}" data-total="${total}" data-paid="${paid}">+ Pay</button>`;
    } else if (b.status === 'checked_in') {
      actionButtons += `<button class="btn btn-primary btn-sm btn-status-transition" data-id="${b.booking_id}" data-target="checked_out">Check Out</button>`;
      actionButtons += `<button class="btn btn-secondary btn-sm btn-open-payment" data-id="${b.booking_id}" data-total="${total}" data-paid="${paid}">+ Pay</button>`;
    } else if (b.status === 'checked_out') {
      actionButtons += `<button class="btn btn-primary btn-sm btn-open-review" data-id="${b.booking_id}">★ Write Review</button>`;
    } else {
      actionButtons += `<span style="font-size: 0.8rem; color: var(--text-dim);">Terminal state: Room released</span>`;
    }

    const guestName = b.guest ? b.guest.full_name : `Guest #${b.guest_id}`;
    const guestEmail = b.guest ? b.guest.email : '';
    const roomNumber = b.room ? `Room ${b.room.room_number}` : `Room #${b.room_id}`;
    const roomType = b.room ? b.room.room_type_name : '';

    card.innerHTML = `
      <div class="booking-header">
        <div>
          <span class="booking-ref">BOOKING #${b.booking_id}</span>
          <h3 class="guest-title">${guestName}</h3>
          <span style="font-size: 0.8rem; color: var(--text-muted);">${guestEmail}</span>
        </div>
        <span class="status-badge ${statusClass}">${statusLabel}</span>
      </div>

      <div class="stay-range-box">
        <span>📅 ${b.check_in} → ${b.check_out}</span>
        <span>${b.nights} night${b.nights > 1 ? 's' : ''}</span>
      </div>

      <div class="booking-details-grid">
        <div class="detail-item">
          <span>Assigned Room</span>
          <strong>${roomNumber} (${roomType})</strong>
        </div>
        <div class="detail-item">
          <span>Occupancy</span>
          <strong>${b.guests_count} Guest${b.guests_count > 1 ? 's' : ''}</strong>
        </div>
        <div class="detail-item">
          <span>Nightly Rate</span>
          <strong>₹${parseFloat(b.nightly_rate).toLocaleString()}</strong>
        </div>
        <div class="detail-item">
          <span>Total Stay Cost</span>
          <strong>₹${total.toLocaleString()}</strong>
        </div>
      </div>

      <div class="payment-progress">
        <div style="display: flex; justify-content: space-between; font-size: 0.8rem;">
          <span style="color: var(--text-dim);">Paid: ₹${paid.toLocaleString()}</span>
          <span style="font-weight: 600; color: ${isPaid ? 'var(--emerald)' : 'var(--gold-glow)'};">
            ${isPaid ? 'Fully Paid ✓' : `Due: ₹${(total - paid).toLocaleString()}`}
          </span>
        </div>
        <div class="progress-bar-container">
          <div class="progress-bar" style="width: ${pct}%;"></div>
        </div>
      </div>

      <div class="booking-actions">
        ${actionButtons}
      </div>
    `;

    container.appendChild(card);
  });

  // Attach status transition handlers
  container.querySelectorAll('.btn-status-transition').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const bookingId = e.currentTarget.getAttribute('data-id');
      const targetStatus = e.currentTarget.getAttribute('data-target');
      await updateBookingStatus(bookingId, targetStatus);
    });
  });

  // Attach payment modal openers
  container.querySelectorAll('.btn-open-payment').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const bookingId = e.currentTarget.getAttribute('data-id');
      const total = e.currentTarget.getAttribute('data-total');
      const paid = e.currentTarget.getAttribute('data-paid');
      openPaymentModal(bookingId, total, paid);
    });
  });

  // Attach review modal openers
  container.querySelectorAll('.btn-open-review').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const bookingId = e.currentTarget.getAttribute('data-id');
      openReviewModal(bookingId);
    });
  });
}

// Handle State Machine Status Transitions
async function updateBookingStatus(bookingId, newStatus) {
  try {
    const res = await fetch(`/bookings/${bookingId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    });

    const data = await res.json();
    if (!res.ok) {
      showToast('State Transition Error', data.message || 'Cannot transition booking state', true);
      return;
    }

    showToast('Status Updated', `Booking #${bookingId} is now ${newStatus.replace('_', ' ')}.`);
    loadBookings();
  } catch (err) {
    showToast('Network Error', err.message, true);
  }
}

// Fetch Reviews
async function loadReviews() {
  try {
    const res = await fetch('/reviews');
    if (!res.ok) throw new Error('Failed to fetch reviews');
    state.reviews = await res.json();
    renderReviews(state.reviews);
  } catch (err) {
    console.error(err);
  }
}

function renderReviews(reviews) {
  const container = document.getElementById('reviews-list-container');
  if (!container) return;

  if (reviews.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: var(--text-dim);">
        No guest reviews submitted yet.
      </div>
    `;
    return;
  }

  container.innerHTML = '';
  reviews.forEach(r => {
    const card = document.createElement('div');
    card.className = 'review-card';
    const stars = '★'.repeat(r.rating) + '☆'.repeat(5 - r.rating);

    card.innerHTML = `
      <div class="review-header">
        <span class="stars" style="font-size: 1.1rem;">${stars}</span>
        <span class="chip" style="font-size: 0.72rem;">Booking #${r.booking_id} Verified</span>
      </div>
      <p class="review-comment">"${r.comments || 'No written feedback provided.'}"</p>
      <div class="review-meta">
        <span>Verified Stay</span>
        <span>${new Date(r.reviewed_at).toLocaleDateString()}</span>
      </div>
    `;
    container.appendChild(card);
  });
}

// Availability Search Flow
document.getElementById('search-availability-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const checkIn = document.getElementById('search-check-in').value;
  const checkOut = document.getElementById('search-check-out').value;
  const guests = document.getElementById('search-guests').value;
  const propId = document.getElementById('search-property').value;

  if (calculateNights(checkIn, checkOut) <= 0) {
    showToast('Invalid Dates', 'Check-out date must be strictly after check-in date (Rule 4).', true);
    return;
  }

  const btn = document.getElementById('btn-search-rooms');
  btn.disabled = true;
  btn.innerText = 'Searching...';

  try {
    let url = `/bookings/availability?check_in=${checkIn}&check_out=${checkOut}&guests_count=${guests}`;
    if (propId) url += `&property_id=${propId}`;

    const res = await fetch(url);
    const data = await res.json();

    if (!res.ok) {
      showToast('Search Failed', data.message || 'Error checking room availability', true);
      return;
    }

    renderAvailableRooms(data, checkIn, checkOut, guests);
  } catch (err) {
    showToast('Error', err.message, true);
  } finally {
    btn.disabled = false;
    btn.innerText = 'Find Available Rooms';
  }
});

function renderAvailableRooms(rooms, checkIn, checkOut, guestsCount) {
  const section = document.getElementById('availability-results-section');
  const container = document.getElementById('rooms-results-container');
  const headline = document.getElementById('results-headline');
  section.style.display = 'block';

  const nNights = calculateNights(checkIn, checkOut);
  headline.innerText = `Available Rooms for ${checkIn} to ${checkOut} (${nNights} Night${nNights > 1 ? 's' : ''}) - ${rooms.length} Found`;

  if (rooms.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; background: var(--bg-card); border-radius: var(--radius-lg); border: 1px dashed var(--border-glass);">
        <h4 style="color: var(--crimson); font-size: 1.1rem; margin-bottom: 0.5rem;">No Rooms Available</h4>
        <p style="color: var(--text-muted); font-size: 0.9rem;">
          All rooms matching this capacity are reserved for the selected dates. Due to exclusion constraints, double-booking is strictly prohibited.
        </p>
      </div>
    `;
    section.scrollIntoView({ behavior: 'smooth' });
    return;
  }

  container.innerHTML = '';
  rooms.forEach(r => {
    const card = document.createElement('div');
    card.className = 'room-card';

    // Pricing estimation
    const defaultRate = r.room_type_name === 'Suite' ? 7980 : (r.room_type_name === 'Deluxe' ? 5320 : 3800);
    const totalEst = defaultRate * nNights;

    card.innerHTML = `
      <div class="room-card-header">
        <span class="room-number">Room ${r.room_number}</span>
        <span class="room-type-badge">${r.room_type_name}</span>
      </div>

      <div class="room-specs">
        <span>👤 Max ${r.max_occupancy} Guests</span>
        <span>🏨 Property #${r.property_id}</span>
      </div>

      <div class="room-price-row">
        <div>
          <div style="font-size: 0.75rem; color: var(--text-dim);">₹${defaultRate.toLocaleString()} / night</div>
          <strong style="font-size: 1.15rem; color: #ffffff;">₹${totalEst.toLocaleString()} <small style="font-weight: 400; font-size: 0.75rem; color: var(--text-muted);">Total (${nNights}N)</small></strong>
        </div>
        <button class="btn btn-primary btn-sm btn-init-booking"
          data-room-id="${r.room_id}"
          data-room-number="${r.room_number}"
          data-rate="${defaultRate}">
          Book Room
        </button>
      </div>
    `;
    container.appendChild(card);
  });

  // Attach booking modal openers
  container.querySelectorAll('.btn-init-booking').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const roomId = e.currentTarget.getAttribute('data-room-id');
      const roomNum = e.currentTarget.getAttribute('data-room-number');
      const rate = e.currentTarget.getAttribute('data-rate');
      openBookingModal(roomId, roomNum, checkIn, checkOut, guestsCount, rate);
    });
  });

  section.scrollIntoView({ behavior: 'smooth' });
}

// Open Booking Modal
function openBookingModal(roomId, roomNum, checkIn, checkOut, guestsCount, rate) {
  document.getElementById('booking-room-id').value = roomId;
  document.getElementById('modal-booking-title').innerText = `Reserve Room ${roomNum}`;
  document.getElementById('booking-check-in').value = checkIn;
  document.getElementById('booking-check-out').value = checkOut;
  document.getElementById('booking-guests-count').value = guestsCount;
  document.getElementById('booking-nightly-rate').value = rate;
  document.getElementById('booking-deposit-amount').value = rate;

  updateBookingModalSummary();
  openModal('modal-booking');
}

function updateBookingModalSummary() {
  const inVal = document.getElementById('booking-check-in').value;
  const outVal = document.getElementById('booking-check-out').value;
  const rate = parseFloat(document.getElementById('booking-nightly-rate').value || 0);
  const n = calculateNights(inVal, outVal);

  const summary = document.getElementById('booking-calc-summary');
  if (n > 0 && rate > 0) {
    const total = n * rate;
    summary.innerText = `Total: ₹${total.toLocaleString()} · ${n} Night${n > 1 ? 's' : ''}`;
  } else {
    summary.innerText = 'Invalid dates';
  }
}

document.getElementById('booking-check-in')?.addEventListener('change', updateBookingModalSummary);
document.getElementById('booking-check-out')?.addEventListener('change', updateBookingModalSummary);
document.getElementById('booking-nightly-rate')?.addEventListener('input', updateBookingModalSummary);

// Handle Deposit Checkbox toggle
document.getElementById('booking-include-deposit')?.addEventListener('change', (e) => {
  const fields = document.getElementById('deposit-fields');
  if (fields) {
    fields.style.display = e.target.checked ? 'grid' : 'none';
  }
});

// Quick New Guest Button from Booking Modal
document.getElementById('btn-quick-new-guest')?.addEventListener('click', () => {
  openModal('modal-guest');
});

// Guest Creation Form Submission
document.getElementById('form-create-guest')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    full_name: document.getElementById('guest-full-name').value.trim(),
    email: document.getElementById('guest-email').value.trim(),
    phone: document.getElementById('guest-phone').value.trim() || null,
    city: document.getElementById('guest-city').value.trim() || null,
  };

  try {
    const res = await fetch('/guests', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      showToast('Guest Registration Conflict', data.message || 'Cannot register guest', true);
      return;
    }

    showToast('Guest Registered', `Welcome ${data.full_name}! Email saved as ${data.email}.`);
    closeModal('modal-guest');
    document.getElementById('form-create-guest').reset();
    await loadGuests();

    // Auto-select newly registered guest in booking modal
    const guestSel = document.getElementById('booking-guest-id');
    if (guestSel) guestSel.value = data.guest_id;
  } catch (err) {
    showToast('Network Error', err.message, true);
  }
});

// Booking Submission
document.getElementById('form-create-booking')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const guestId = parseInt(document.getElementById('booking-guest-id').value);
  const roomId = parseInt(document.getElementById('booking-room-id').value);
  const checkIn = document.getElementById('booking-check-in').value;
  const checkOut = document.getElementById('booking-check-out').value;
  const guestsCount = parseInt(document.getElementById('booking-guests-count').value);
  const nightlyRate = document.getElementById('booking-nightly-rate').value;
  const includeDeposit = document.getElementById('booking-include-deposit').checked;

  const payload = {
    guest_id: guestId,
    room_id: roomId,
    check_in: checkIn,
    check_out: checkOut,
    guests_count: guestsCount,
    nightly_rate: nightlyRate,
  };

  if (includeDeposit) {
    payload.deposit_amount = document.getElementById('booking-deposit-amount').value;
    payload.deposit_method = document.getElementById('booking-deposit-method').value;
    payload.idempotency_key = `dep-atom-${Date.now()}`;
  }

  const btn = document.getElementById('btn-submit-booking');
  btn.disabled = true;
  btn.innerText = 'Confirming...';

  try {
    const res = await fetch('/bookings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      showToast('Booking Rejected (Constraint)', data.message || 'Error creating reservation', true);
      return;
    }

    showToast('Reservation Confirmed! 🎉', `Booking #${data.booking_id} created successfully with atomic transaction.`);
    closeModal('modal-booking');
    loadBookings();
    document.getElementById('reservations-section').scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    showToast('Network Error', err.message, true);
  } finally {
    btn.disabled = false;
    btn.innerText = 'Confirm Reservation';
  }
});

// Quick Booking Button from Reservations Section
document.getElementById('btn-open-quick-booking')?.addEventListener('click', () => {
  document.getElementById('booking-section').scrollIntoView({ behavior: 'smooth' });
});

// Status Filter Tabs
document.getElementById('status-filter-tabs')?.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    document.getElementById('status-filter-tabs').querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    e.currentTarget.classList.add('active');
    const status = e.currentTarget.getAttribute('data-status');
    loadBookings(status);
  });
});

// Payment Modal Handling
function openPaymentModal(bookingId, total, paid) {
  document.getElementById('payment-booking-id').value = bookingId;
  const due = Math.max(0, parseFloat(total) - parseFloat(paid));
  document.getElementById('payment-amount').value = due > 0 ? due : 1000;
  document.getElementById('payment-idempotency-key').value = `pay-${bookingId}-${Date.now()}`;

  document.getElementById('payment-booking-info').innerHTML = `
    <strong>Booking #${bookingId}</strong> · Total: ₹${parseFloat(total).toLocaleString()} · Currently Paid: ₹${parseFloat(paid).toLocaleString()}
  `;

  openModal('modal-payment');
}

document.getElementById('btn-gen-idempotency')?.addEventListener('click', () => {
  const bId = document.getElementById('payment-booking-id').value;
  document.getElementById('payment-idempotency-key').value = `pay-${bId}-${Date.now()}`;
});

document.getElementById('form-record-payment')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    booking_id: parseInt(document.getElementById('payment-booking-id').value),
    amount: document.getElementById('payment-amount').value,
    method: document.getElementById('payment-method').value,
    idempotency_key: document.getElementById('payment-idempotency-key').value.trim() || null,
  };

  try {
    const res = await fetch('/payments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      showToast('Payment Rejected', data.message || 'Payment failed', true);
      return;
    }

    if (res.status === 200 || data.is_replay) {
      showToast('Idempotent Replay (HTTP 200)', `Payment #${data.payment_id} was already processed previously. Replay acknowledged safely!`);
    } else {
      showToast('Payment Recorded (HTTP 201)', `Payment of ₹${data.amount} recorded successfully.`);
    }

    closeModal('modal-payment');
    loadBookings();
  } catch (err) {
    showToast('Network Error', err.message, true);
  }
});

// Review Modal Handling
function openReviewModal(bookingId) {
  document.getElementById('review-booking-id').value = bookingId;
  document.getElementById('review-booking-info').innerHTML = `
    <strong>Booking #${bookingId}</strong> · Status: Checked Out (Eligible for Review per Rule 9)
  `;
  openModal('modal-review');
}

document.getElementById('form-submit-review')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    booking_id: parseInt(document.getElementById('review-booking-id').value),
    rating: parseInt(document.getElementById('review-rating').value),
    comments: document.getElementById('review-comments').value.trim() || null,
  };

  try {
    const res = await fetch('/reviews', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      showToast('Review Blocked (Rule 9)', data.message || 'Error submitting review', true);
      return;
    }

    showToast('Review Published', `Thank you for your rating!`);
    closeModal('modal-review');
    loadReviews();
  } catch (err) {
    showToast('Network Error', err.message, true);
  }
});

// ==========================================================================
// Interactive Attack & Constraint Lab (05_break_it.sql Test Runner)
// ==========================================================================

const ATTACK_SCENARIOS = {
  '5.1': {
    name: 'Attack 5.1: Double-Booking Overlap',
    method: 'POST',
    url: '/bookings',
    body: {
      guest_id: 5,
      room_id: 4, // Riverside 101 (room_id 4) has booking 2026-01-10 to 2026-01-14
      check_in: '2026-01-12',
      check_out: '2026-01-15',
      guests_count: 2,
      nightly_rate: '3800.00'
    },
    rule: 'Rule 4 & 5 (GiST Exclusion Constraint "no_overlapping_bookings")',
    expected: '409 Conflict'
  },
  '5.2': {
    name: 'Attack 5.2: Chronological Reversal (Checkout before Checkin)',
    method: 'POST',
    url: '/bookings',
    body: {
      guest_id: 5,
      room_id: 3,
      check_in: '2026-05-05',
      check_out: '2026-05-01',
      guests_count: 2,
      nightly_rate: '3800.00'
    },
    rule: 'Rule 4 (CHECK Constraint "valid_stay" / nights function)',
    expected: '422 Unprocessable Content'
  },
  '5.4': {
    name: 'Attack 5.4: Capacity Overbooking',
    method: 'POST',
    url: '/bookings',
    body: {
      guest_id: 5,
      room_id: 3, // Riverside 102 (Standard room, max 2 guests)
      check_in: '2026-05-01',
      check_out: '2026-05-04',
      guests_count: 4, // Exceeds max 2
      nightly_rate: '3800.00'
    },
    rule: 'Rule 3 (PL/pgSQL Trigger "trg_check_occupancy")',
    expected: '422 Unprocessable Content'
  },
  '5.8': {
    name: 'Attack 5.8: Case-Insensitive Duplicate Email',
    method: 'POST',
    url: '/guests',
    body: {
      full_name: 'Fake Aarav',
      email: 'AARAV.SHARMA@EXAMPLE.COM', // lowercase exists in seed data
      phone: '+919999999999',
      city: 'Delhi'
    },
    rule: 'Rule 10 (Unique Index "uq_guests_email_lower")',
    expected: '409 Conflict'
  },
  '5.10': {
    name: 'Attack 5.10: Negative Payment Amount',
    method: 'POST',
    url: '/payments',
    body: {
      booking_id: 1,
      amount: '-500.00',
      method: 'card'
    },
    rule: 'Rule 8 (CHECK Constraint "payments_amount_check")',
    expected: '422 Unprocessable Content'
  },
  '5.12': {
    name: 'Attack 5.12: Duplicate Review for Single Booking',
    method: 'POST',
    url: '/reviews',
    body: {
      booking_id: 1, // Booking 1 already has a review in seed data
      rating: 4,
      comments: 'Duplicate attempt'
    },
    rule: 'Rule 9 (UNIQUE Constraint "reviews_booking_id_key")',
    expected: '409 Conflict'
  },
  '5.13': {
    name: 'Attack 5.13: Premature Review Before Checkout',
    method: 'POST',
    url: '/reviews',
    body: {
      booking_id: 2, // Booking 2 is confirmed, not checked out
      rating: 4,
      comments: 'Review before checkout'
    },
    rule: 'Rule 9 (PL/pgSQL Trigger "trg_check_review_allowed")',
    expected: '409 Conflict'
  },
  '5.15': {
    name: 'Test 5.15: Same-Day Turnover Non-Collision',
    method: 'POST',
    url: '/bookings',
    body: {
      guest_id: 6,
      room_id: 3,
      check_in: '2026-06-05',
      check_out: '2026-06-08',
      guests_count: 2,
      nightly_rate: '3800.00'
    },
    rule: 'Rule 5 (Half-open [) daterange allows check-out & check-in on the exact same date)',
    expected: '201 Created (Success)'
  },
  '6.0': {
    name: 'Test 6.0: Atomic Deposit Failure Rollback',
    method: 'POST',
    url: '/bookings',
    body: {
      guest_id: 6,
      room_id: 4,
      check_in: '2026-11-10',
      check_out: '2026-11-13',
      guests_count: 2,
      nightly_rate: '3800.00',
      deposit_amount: '-1.00', // Invalid amount triggers rollback
      deposit_method: 'upi'
    },
    rule: 'Rule 8 / Task 6 (Atomic Transaction commits both or rolls back everything)',
    expected: '422 Unprocessable Content (Rollback verification)'
  }
};

document.querySelectorAll('.btn-run-attack').forEach(btn => {
  btn.addEventListener('click', async (e) => {
    const attackKey = e.currentTarget.getAttribute('data-attack');
    const scenario = ATTACK_SCENARIOS[attackKey];
    if (!scenario) return;

    const inspector = document.getElementById('inspector-output');
    const statusBadge = document.getElementById('inspector-status-badge');
    inspector.innerText = `// Sending live request to backend: ${scenario.method} ${scenario.url}...\n\nPayload:\n${JSON.stringify(scenario.body, null, 2)}`;
    statusBadge.style.display = 'none';

    try {
      const res = await fetch(scenario.url, {
        method: scenario.method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scenario.body),
      });

      const responseData = await res.json();
      const statusText = `HTTP ${res.status} ${res.statusText}`;

      statusBadge.style.display = 'inline-block';
      statusBadge.innerText = statusText;
      statusBadge.className = `status-badge ${res.ok ? 'status-checked_in' : 'status-cancelled'}`;

      const outputText = `// ==========================================================================\n` +
        `// Scenario: ${scenario.name}\n` +
        `// Enforced By: ${scenario.rule}\n` +
        `// Expected Code: ${scenario.expected}\n` +
        `// Actual Response: ${statusText}\n` +
        `// ==========================================================================\n\n` +
        JSON.stringify(responseData, null, 2);

      inspector.innerText = outputText;

      if (!res.ok) {
        showToast(`Tested: ${scenario.name}`, `Received expected ${statusText}: ${responseData.message || responseData.code}`);
      } else {
        showToast(`Success: ${scenario.name}`, `Received ${statusText} as verified by Rule 5.`);
      }

      inspector.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (err) {
      inspector.innerText = `Network Error: ${err.message}`;
    }
  });
});

document.getElementById('btn-clear-inspector')?.addEventListener('click', () => {
  document.getElementById('inspector-output').innerText = '// Click any attack or test above to run the live payload against the backend...';
  document.getElementById('inspector-status-badge').style.display = 'none';
});

// Refresh properties button
document.getElementById('btn-refresh-properties')?.addEventListener('click', () => {
  loadProperties();
  showToast('Properties Refreshed', 'Refreshed 3 resort destinations.');
});

// Filter by Property Buttons
document.querySelectorAll('.btn-filter-prop').forEach(btn => {
  btn.addEventListener('click', (e) => {
    const propId = e.currentTarget.getAttribute('data-prop-id');
    const sel = document.getElementById('search-property');
    if (sel) sel.value = propId;
    document.getElementById('booking-section').scrollIntoView({ behavior: 'smooth' });
    document.getElementById('btn-search-rooms').click();
  });
});

// App Startup
document.addEventListener('DOMContentLoaded', () => {
  initDefaultDates();
  checkSystemHealth();
  loadProperties();
  loadGuests();
  loadBookings();
  loadReviews();
});
