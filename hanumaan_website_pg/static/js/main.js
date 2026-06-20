// ============================================================
//  Hanumaan Luxury Ladies PG — Main JavaScript
// ============================================================

// ── Navbar scroll ──
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
  navbar?.classList.toggle('scrolled', window.scrollY > 50);
});

// ── Mobile hamburger ──
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('navLinks');
hamburger?.addEventListener('click', () => {
  navLinks?.classList.toggle('open');
  hamburger.setAttribute('aria-expanded', navLinks?.classList.contains('open') ? 'true' : 'false');
});
navLinks?.querySelectorAll('a').forEach(a => {
  a.addEventListener('click', () => navLinks.classList.remove('open'));
});

// ── Hero Slider ──
const slides = document.querySelectorAll('.hero-slide');
const dots = document.querySelectorAll('.dot');
let current = 0;
let sliderTimer;

function goToSlide(index) {
  slides[current]?.classList.remove('active');
  dots[current]?.classList.remove('active');
  current = (index + slides.length) % slides.length;
  slides[current]?.classList.add('active');
  dots[current]?.classList.add('active');
}

function startSlider() {
  sliderTimer = setInterval(() => goToSlide(current + 1), 5000);
}

dots.forEach((dot, i) => {
  dot.addEventListener('click', () => {
    clearInterval(sliderTimer);
    goToSlide(i);
    startSlider();
  });
});

if (slides.length > 0) startSlider();

// ── Counter animation ──
function animateCounters() {
  document.querySelectorAll('.stat-num').forEach(el => {
    const target = parseInt(el.dataset.target, 10);
    if (!target) return;
    const duration = 1800;
    const step = Math.ceil(target / (duration / 16));
    let count = 0;
    const timer = setInterval(() => {
      count = Math.min(count + step, target);
      el.textContent = count;
      if (count >= target) clearInterval(timer);
    }, 16);
  });
}

const statsSection = document.querySelector('.stats');
if (statsSection) {
  let counted = false;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !counted) {
        counted = true;
        animateCounters();
        observer.disconnect();
      }
    });
  }, { threshold: 0.3 });
  observer.observe(statsSection);
}

// ── Enquiry Form ──
document.querySelectorAll('.enquiry-form, #contactEnquiryForm').forEach(form => {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msgEl = form.querySelector('.form-message');
    const btn = form.querySelector('.btn-submit');
    const data = new FormData(form);
    const name = data.get('name') || '';
    const phone = data.get('phone') || '';
    const roomType = data.get('enquiry_type') || '';
    const sharing = data.get('company_college') || '';

    btn.textContent = 'Sending...';
    btn.disabled = true;
    if (msgEl) { msgEl.textContent = ''; msgEl.className = 'form-message'; }

    try {
      const res = await fetch('/enquire', { method: 'POST', body: data });
      const json = await res.json();
      if (msgEl) {
        msgEl.textContent = json.message;
        msgEl.className = 'form-message ' + (json.success ? 'success' : 'error');
      }
      if (json.success) {
        form.reset();
        // Auto WhatsApp message sent to PG with user details + confirmation to user
        const waMsg = encodeURIComponent(
          `Hi Hanumaan Luxury Ladies PG! 🙏\n\nI have submitted an enquiry on your website.\n\n` +
          `👤 Name: ${name}\n📞 Phone: ${phone}\n🛏️ Room Type: ${roomType}\n👥 Sharing: ${sharing}\n\n` +
          `Please contact me at your earliest convenience.\n\nThank you! 😊`
        );
        setTimeout(() => {
          window.open(`https://wa.me/917092189999?text=${waMsg}`, '_blank');
        }, 1500);
      }
    } catch {
      if (msgEl) {
        msgEl.textContent = 'Something went wrong. Please call us: +91 70921 89999';
        msgEl.className = 'form-message error';
      }
    } finally {
      btn.textContent = 'Send Enquiry 🚀';
      btn.disabled = false;
    }
  });
});

// ── Fade-in on scroll ──
const fadeEls = document.querySelectorAll(
  '.facility-card, .testimonial-card, .why-card, .facility-detail-card, .contact-info-card, .gallery-item'
);
const fadeObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
    }
  });
}, { threshold: 0.08 });

fadeEls.forEach(el => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(20px)';
  el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
  fadeObserver.observe(el);
});

// ── Gallery lightbox ──
const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightboxImg');
const galleryItems = document.querySelectorAll('.gallery-item[data-src]');
let lbIndex = 0;

function openLightbox(index) {
  lbIndex = index;
  lightboxImg.src = galleryItems[lbIndex].dataset.src;
  lightboxImg.alt = galleryItems[lbIndex].dataset.title || '';
  lightbox?.classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeLightbox() {
  lightbox?.classList.remove('open');
  document.body.style.overflow = '';
}
function prevLb() { lbIndex = (lbIndex - 1 + galleryItems.length) % galleryItems.length; lightboxImg.src = galleryItems[lbIndex].dataset.src; }
function nextLb() { lbIndex = (lbIndex + 1) % galleryItems.length; lightboxImg.src = galleryItems[lbIndex].dataset.src; }

galleryItems.forEach((item, i) => item.addEventListener('click', () => openLightbox(i)));
document.getElementById('lightboxClose')?.addEventListener('click', closeLightbox);
document.getElementById('lightboxPrev')?.addEventListener('click', prevLb);
document.getElementById('lightboxNext')?.addEventListener('click', nextLb);
lightbox?.addEventListener('click', (e) => { if (e.target === lightbox) closeLightbox(); });
document.addEventListener('keydown', (e) => {
  if (!lightbox?.classList.contains('open')) return;
  if (e.key === 'Escape') closeLightbox();
  if (e.key === 'ArrowLeft') prevLb();
  if (e.key === 'ArrowRight') nextLb();
});

// ── Gallery filter ──
const filterBtns = document.querySelectorAll('.filter-btn');
filterBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    filterBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const cat = btn.dataset.cat;
    document.querySelectorAll('.gallery-item').forEach(item => {
      item.style.display = (cat === 'all' || item.dataset.cat === cat) ? '' : 'none';
    });
  });
});

// ── FAQ Accordion ──
document.querySelectorAll('.faq-question').forEach(btn => {
  btn.addEventListener('click', () => {
    const item = btn.parentElement;
    const isOpen = item.classList.contains('open');
    document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('open'));
    if (!isOpen) item.classList.add('open');
  });
});
