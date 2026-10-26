(() => {
  try {
    const views = JSON.parse(document.getElementById('views').textContent),
      mode = document.getElementById('mode'),
      style = document.getElementById('style');
    const key = () => mode.value + '_' + style.value;
    const render = () => document.getElementById('chart').innerHTML = views[key()];
    mode.onchange = style.onchange = render;
    document.getElementById('save').onclick = () => {
      const u = URL.createObjectURL(new Blob([views[key()]], {
          type: 'image/svg+xml'
        })),
        a = document.createElement('a');
      a.href = u;
      a.download = 'word_lengths_' + key() + '.svg';
      a.click();
      setTimeout(() => URL.revokeObjectURL(u), 1000)
    };
    document.getElementById('controls').hidden = false
  } catch (e) {}
})()
