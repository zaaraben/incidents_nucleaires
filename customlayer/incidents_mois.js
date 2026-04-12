mviewer.customLayers.incidents_mois = {

  layer: new ol.layer.Vector({
    source: new ol.source.Vector()
  }),

  init: function () {
    var self = this;

    self.layer.setStyle(function (feature) {
      var level = parseInt(feature.get('niveau_ines') || 0, 10);

      var color;
      if (level >= 4) {
        color = '#c62828';
      } else if (level >= 2) {
        color = '#ef6c00';
      } else {
        color = '#fbc02d';
      }

      return new ol.style.Style({
        image: new ol.style.RegularShape({
          points: 3,
          radius: 10,
          angle: 0,
          fill: new ol.style.Fill({
            color: color
          }),
          stroke: new ol.style.Stroke({
            color: '#ffffff',
            width: 2
          })
        })
      });
    });

    fetch('apps/incidents_nucleaires/data/incidents_nucleaires.geojson')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var source = self.layer.getSource();
        var incidentsParSite = {};

        data.features.forEach(function (f) {
          var p = f.properties || {};
          var g = f.geometry || {};

          if (g.type !== 'Point' || !g.coordinates || g.coordinates.length < 2) {
            return;
          }

          var site = p.nom_site || 'Site inconnu';

          if (!incidentsParSite[site]) {
            incidentsParSite[site] = 0;
          }

          var index = incidentsParSite[site];
          incidentsParSite[site]++;

          var lon = g.coordinates[0];
          var lat = g.coordinates[1];

          var angle = (index * 45) * Math.PI / 180;
          var offset = 0.08;
          var lonOffset = lon + (Math.cos(angle) * offset);
          var latOffset = lat + (Math.sin(angle) * offset);

          var feature = new ol.Feature({
            geometry: new ol.geom.Point(
              ol.proj.fromLonLat([lonOffset, latOffset])
            )
          });

          feature.setProperties({
            id: p.id || '',
            nom_site: p.nom_site || '',
            niveau_ines: p.niveau_ines || '',
            niveau_ines_label: p.niveau_ines_label || '',
            date_incident: p.date_incident || '',
            date_declaration: p.date_declaration || '',
            date_publication: p.date_publication || '',
            description: p.description || '',
            hyperlien: p.hyperlien || ''
          });

          source.addFeature(feature);
        });
      })
      .catch(function (err) {
        console.error('[incidents_mois] Erreur chargement GeoJSON :', err);
      });
  }
};