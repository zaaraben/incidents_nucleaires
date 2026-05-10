/* global ol, CustomLayer */

var layerid = "sites_nucleaires";
var _centralesFilterActive = false;

function _centralColor(nbIncidents, inesMax) {
  if (nbIncidents === 0) return "rgba(160,160,160,0.65)";
  if (inesMax >= 2) return "rgba(180,60,0,0.9)";
  return "rgba(169,138,54,0.9)";
}

function centralStyleFn(feature) {
  var nbIncidents = feature.get("nb_incidents_affiches") || 0;
  var inesMax = feature.get("ines_max") || 0;

  if (_centralesFilterActive && nbIncidents === 0) {
    return new ol.style.Style({});
  }

  if (nbIncidents === 0) {
    var nbTotal = feature.get("nb_total_incidents") || 0;
    var radiusTotal = Math.max(8, Math.min(Math.round(nbTotal / 10), 25));
    return new ol.style.Style({
      image: new ol.style.Circle({
        radius: radiusTotal,
        fill: new ol.style.Fill({ color: "rgba(160,160,160,0.65)" }),
        stroke: new ol.style.Stroke({ color: "rgba(100,100,100,0.7)", width: 1 })
      })
    });
  }

  var radius = Math.min(8 + nbIncidents, 20);

  return new ol.style.Style({
    image: new ol.style.RegularShape({
      points: 3,
      radius: radius,
      rotation: 0,
      fill: new ol.style.Fill({ color: _centralColor(nbIncidents, inesMax) }),
      stroke: new ol.style.Stroke({ color: "rgba(0,0,0,0.9)", width: 2 })
    })
  });
}

function centralesToggleFilter() {
  _centralesFilterActive = !_centralesFilterActive;
  var btn = document.getElementById("btn-centrales-filter");
  if (btn) {
    btn.classList.toggle("active", _centralesFilterActive);
    btn.title = _centralesFilterActive
      ? "Afficher toutes les centrales"
      : "Afficher uniquement les centrales avec incidents sur la période";
  }
  var src = mviewer.getLayer(layerid).layer.getSource();
  src.getFeatures().forEach(function(f) {
    f.setStyle(centralStyleFn(f));
  });
}

var _centralesSource = new ol.source.Vector({
  url: "apps/incidents_nucleaires/data/centrales_incidents.geojson",
  format: new ol.format.GeoJSON({
    dataProjection: "EPSG:4326",
    featureProjection: "EPSG:3857"
  })
});

_centralesSource.on("addfeature", function(evt) {
  var feature = evt.feature;
  var incidents = feature.get("incidents") || [];
  var cards = incidents.map(function(inc) {
    var ines = (inc.niveau_ines !== null && inc.niveau_ines !== undefined)
      ? "INES " + inc.niveau_ines : "NC";
    var date = inc.date_publication || inc.date_declaration || inc.date_incident || "";
    var level = inc.niveau_ines;
    var inesClass = (level === null || level === undefined) ? "mv-inc-nc"
      : level >= 2 ? "mv-inc-high" : "mv-inc-1";
    var header = "<span class='mv-inc-ines'>" + ines + "</span>" +
      (date ? "<span class='mv-inc-date'>" + date + "</span>" : "");
    var desc = inc.description
      ? "<p class='mv-inc-desc'>" + inc.description + "</p>" : "";
    var link = inc.url_incident
      ? "<a class='mv-inc-link' href='" + inc.url_incident + "' target='_blank' rel='noopener'>Voir la fiche →</a>" : "";
    return "<div class='mv-inc-card " + inesClass + "'>" + header + desc + link + "</div>";
  });
  var html = cards.length
    ? "<div class='mv-inc-list'>" + cards.join("") + "</div>"
    : "<p class='mv-centrales-no-incident'>Aucun incident sur la période affichée</p>";
  feature.set("incidents_tableau", html);
});

var layer = new ol.layer.Vector({
  source: _centralesSource,
  style: centralStyleFn
});

// Dessous des alertes (zIndex 100)
layer.setZIndex(10);

function _initCentralesToggle() {
  if (typeof mviewer !== "undefined" && mviewer.getMap) {
    mviewer.getMap().once("rendercomplete", function() {
      if ($("#btn-centrales-filter").length === 0) {
        var $btn = $(
          '<button id="btn-centrales-filter" class="btn btn-default btn-raised" ' +
          'onclick="centralesToggleFilter();" ' +
          'title="Afficher uniquement les centrales avec incidents sur la période" ' +
          'tabindex="116">' +
          '<span class="glyphicon glyphicon-filter" aria-hidden="true"></span>' +
          "</button>"
        );
        $btn.css("color", "#ff6b6b");
        $("#toolstoolbar").append($btn);
      }
    });
  } else {
    setTimeout(_initCentralesToggle, 150);
  }
}

_initCentralesToggle();

new CustomLayer(layerid, layer);
