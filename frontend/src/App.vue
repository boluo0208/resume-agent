<template>
  <div class="app-root">
    <header class="app-masthead stagger-1">
      <div class="masthead-inner">
        <span class="logo-mark">RA</span>
        <div>
          <p class="eyebrow">Multi-Agent System</p>
          <p class="masthead-title">简历分析工作台</p>
        </div>
        <div class="masthead-line"></div>
      </div>
    </header>
    <Analyze />
  </div>
</template>

<script setup>
import Analyze from './views/Analyze.vue'
</script>

<style scoped>
.app-root {
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

.app-masthead {
  padding: var(--space-lg) var(--space-lg) 0;
  max-width: 1480px;
  margin: 0 auto;
}

.masthead-inner {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding-bottom: var(--space-lg);
  border-bottom: 1px solid var(--color-border);
  position: relative;
}

.logo-mark {
  font-family: var(--font-display);
  font-size: 1.4rem;
  font-weight: 900;
  color: var(--color-gold);
  letter-spacing: 0.04em;
  width: 44px;
  height: 44px;
  display: grid;
  place-content: center;
  border: 1px solid var(--color-gold-dim);
  border-radius: var(--radius-sm);
  background: rgba(139,105,20,0.06);
}

.masthead-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-text);
}

.masthead-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, var(--color-border), transparent);
  margin-left: var(--space-lg);
}

@media (max-width: 640px) {
  .masthead-line { display: none; }
  .app-masthead { padding: var(--space-md) var(--space-md) 0; }
}
</style>
