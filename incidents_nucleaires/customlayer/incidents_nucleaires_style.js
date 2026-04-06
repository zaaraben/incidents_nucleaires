var incidents_nucleaires_style = (function () {
  function getColor(level) {
    if (level >= 4) { return '#c62828'; }
    if (level >= 2) { return '#ef6c00'; }
    return '#2e7d32';
  }

  return function(feature) {
    var level = parseInt(feature.get('niveau_ines') || 0, 10);
    var radius = level >= 4 ? 10 : (level >= 2 ? 8 : 6);
    return new ol.style.Style({
      image: new ol.style.Circle({
        radius: radius,
        fill: new ol.style.Fill({ color: getColor(level) }),
        stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
      })
    });
  };
})();
