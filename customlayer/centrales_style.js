var centrales_style = (function () {
  function getRadius(total) {
    var minValue = 80;
    var maxValue = 250;

    var minRadius = 10;
    var maxRadius = 32;

    if (total <= minValue) return minRadius;
    if (total >= maxValue) return maxRadius;

    var ratio = (total - minValue) / (maxValue - minValue);
    ratio = Math.pow(ratio, 0.7);

    return minRadius + ratio * (maxRadius - minRadius);
  }

  function getColor(total) {
    if (total >= 220) return '#b71c1c';
    if (total >= 180) return '#d84315';
    if (total >= 140) return '#f9a825';
    if (total >= 100) return '#7cb342';
    return '#2e7d32';
  }

  return function (feature) {
    var total = parseInt(feature.get('nombre_total_incidents') || 0, 10);
    var radius = getRadius(total);

    return new ol.style.Style({
      image: new ol.style.Circle({
        radius: radius,
        fill: new ol.style.Fill({
          color: getColor(total)
        }),
        stroke: new ol.style.Stroke({
          color: '#ffffff',
          width: 1.5
        })
      }),
      text: new ol.style.Text({
        text: String(total),
        font: 'bold 10px sans-serif',
        fill: new ol.style.Fill({ color: '#ffffff' }),
        offsetY: 1
      })
    });
  };
})();