// fix-svg-viewbox.js
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('svg').forEach(svg => {
    const viewBox = svg.getAttribute('viewBox');
    if (viewBox && viewBox.includes('%')) {
      const parts = viewBox.split(' ');
      if (parts.length === 4) {
        const newParts = parts.map(part => {
          const clean = part.replace('%', '').replace('px', '');
          const num = parseFloat(clean);
          return isNaN(num) ? 0 : num;
        });
        svg.setAttribute('viewBox', newParts.join(' '));
        console.log(`✅ Fixed viewBox: ${viewBox} → ${newParts.join(' ')}`);
      }
    }
  });
});