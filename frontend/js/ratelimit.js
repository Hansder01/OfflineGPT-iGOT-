/**
 * Offline GPT — Security Rate Limit & Cooldown Timer Manager
 */

let cooldownInterval = null;
let currentCooldownSeconds = 0;

window.updateRateLimitUI = function(info) {
    if (!info) return;

    const gaugeUsedVal = document.getElementById('gauge-used-val');
    const gaugeMaxVal = document.getElementById('gauge-max-val');
    const gaugeCircle = document.querySelector('.gauge-circle');
    
    const navQuotaText = document.getElementById('quota-text');
    const statusPill = document.getElementById('ratelimit-status-pill');
    const remainingCountVal = document.getElementById('remaining-count-val');
    const cooldownTimerVal = document.getElementById('cooldown-timer-val');
    
    const banner = document.getElementById('rate-limit-banner');
    const bannerMsg = document.getElementById('cooldown-banner-msg');
    const bannerSecs = document.getElementById('cooldown-seconds-val');

    const count = info.current_count || 0;
    const max = info.max_prompts || 10;
    const remaining = info.remaining !== undefined ? info.remaining : max - count;
    const resetSecs = info.reset_in_seconds || 0;
    const isCooldown = info.cooldown_active || count >= max;

    if (gaugeUsedVal) gaugeUsedVal.innerText = count;
    if (gaugeMaxVal) gaugeMaxVal.innerText = `/ ${max} Prompts`;
    if (navQuotaText) navQuotaText.innerText = `${count}/${max} Prompts`;
    if (remainingCountVal) remainingCountVal.innerText = remaining;

    // Update gauge visual conic gradient
    if (gaugeCircle) {
        const percent = Math.min(100, (count / max) * 100);
        const color = isCooldown ? 'var(--accent-rose)' : 'var(--accent-cyan)';
        gaugeCircle.style.background = `conic-gradient(${color} ${percent * 3.6}deg, rgba(255, 255, 255, 0.05) 0deg)`;
    }

    if (isCooldown) {
        if (statusPill) {
            statusPill.className = 'pill pill-danger';
            statusPill.innerText = 'Cooldown Active 🔴';
        }
        
        if (banner) banner.classList.remove('hidden');
        if (bannerMsg && info.message) bannerMsg.innerText = info.message;
        
        startCooldownTimer(resetSecs);
    } else {
        if (statusPill) {
            statusPill.className = 'pill pill-success';
            statusPill.innerText = 'Operational 🟢';
        }
        if (banner) banner.classList.add('hidden');
        if (cooldownTimerVal) cooldownTimerVal.innerText = '0 seconds';
        stopCooldownTimer();
    }
};

window.handleRateLimitExceeded = function(detail) {
    window.updateRateLimitUI({
        cooldown_active: true,
        current_count: detail.current_count || 10,
        max_prompts: detail.max_prompts || 10,
        remaining: 0,
        reset_in_seconds: detail.reset_in_seconds || 300,
        message: detail.message || "Rate limit reached. Please wait for cooldown timer."
    });
};

function startCooldownTimer(seconds) {
    currentCooldownSeconds = seconds;
    stopCooldownTimer();

    const timerVal = document.getElementById('cooldown-timer-val');
    const bannerSecs = document.getElementById('cooldown-seconds-val');

    function tick() {
        if (currentCooldownSeconds <= 0) {
            stopCooldownTimer();
            window.loadRateLimitStatus();
            return;
        }

        if (timerVal) timerVal.innerText = `${currentCooldownSeconds} seconds`;
        if (bannerSecs) bannerSecs.innerText = currentCooldownSeconds;
        currentCooldownSeconds--;
    }

    tick();
    cooldownInterval = setInterval(tick, 1000);
}

function stopCooldownTimer() {
    if (cooldownInterval) {
        clearInterval(cooldownInterval);
        cooldownInterval = null;
    }
}

window.loadRateLimitStatus = async function() {
    try {
        const info = await ApiClient.getRateLimitStatus();
        window.updateRateLimitUI(info);
    } catch (e) {
        console.error("Error fetching rate limit status:", e);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    window.loadRateLimitStatus();
});
