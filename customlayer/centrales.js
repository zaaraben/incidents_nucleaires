mviewer.customLayers.centrales = {

  layer: new ol.layer.Vector({
    source: new ol.source.Vector()
  }),

  init: function () {
    var self = this;

    function getRadius(total) {
      var minValue = 80;
      var maxValue = 292;

      var minRadius = 10;
      var maxRadius = 32;

      if (total <= minValue) return minRadius;
      if (total >= maxValue) return maxRadius;

      var ratio = (total - minValue) / (maxValue - minValue);
      ratio = Math.pow(ratio, 0.7);

      return minRadius + ratio * (maxRadius - minRadius);
    }

    function getColor(total) {
      if (total >= 250) return '#b71c1c';
      if (total >= 200) return '#d84315';
      if (total >= 150) return '#f9a825';
      if (total >= 100) return '#7cb342';
      return '#2e7d32';
    }

    self.layer.setStyle(function (feature) {
      var total = parseInt(feature.get('nombre_total_incidents') || 0, 10);

      return new ol.style.Style({
        image: new ol.style.Circle({
          radius: getRadius(total),
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
    });

    fetch('apps/incidents_nucleaires/data/centrales.geojson')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var format = new ol.format.GeoJSON({
          featureProjection: 'EPSG:3857'
        });

        var features = format.readFeatures(data);
        self.layer.getSource().addFeatures(features);
      })
      .catch(function (err) {
        console.error('[centrales] Erreur chargement GeoJSON :', err);
      });
  }
};