(() => {
  try {
    const views = JSON.parse(document.getElementById('views').textContent),
      mode = document.getElementById('mode'),
      scale = document.getElementById('scale');

    function render() {
      document.getElementById('chart').innerHTML = views[mode.value][scale.value]
    }
    mode.onchange = scale.onchange = render;
    document.getElementById('save').onclick = () => {
      let url = URL.createObjectURL(new Blob([views[mode.value][scale.value]], {
        type: 'image/svg+xml'
      }));
      let a = document.createElement('a');
      a.href = url;
      a.download = 'eva_word_positions_' + mode.value + '_' + scale.value + '.svg';
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    };
    document.getElementById('controls').hidden = false
  } catch (e) {}
})()
