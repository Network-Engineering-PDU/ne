am5.ready(function () {
  var date = new Date();
  date.setHours(0, 0, 0, 0);
  var value = 0;
  function generateData() {
    value = Math.round(Math.random() * 10 - 4.2 + value);
    am5.time.add(date, "minute", 1);
    return {
      date: date.getTime(),
      value: value,
    };
  }

  function generateDatas(count) {
    var data = [];
    for (var i = 0; i < count; ++i) {
      data.push(generateData());
    }
    return data;
  }

  const data1 = [];
  for (var i = 0; i < 6; i++) {
    data1.push({ name: `Input ${i + 1}`, items: generateDatas(60) });
    date = new Date();
    date.setHours(0, 0, 0, 0);
    value = 0;
  }

  drawig("chartVoltage", DATA_FOR_CHARTS, 'voltage', 'V');
  drawig("chartPhaseCurrent", DATA_FOR_CHARTS, 'current', 'A');
  drawig("chartActivePower", DATA_FOR_CHARTS, 'active_power', 'W');
  drawig("chartPowerFactor", DATA_FOR_CHARTS, 'power_factor', '');
}); // end am5.ready()

function drawig(ref, data = [], key='', um='') {
  console.log(data);

  var root = am5.Root.new(ref);

  // Set themes
  // https://www.amcharts.com/docs/v5/concepts/themes/
  root.setThemes([am5themes_Animated.new(root)]);

  // Create chart
  // https://www.amcharts.com/docs/v5/charts/xy-chart/
  var chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: true,
        panY: true,
        wheelX: "panX",
        wheelY: "zoomX",
        maxTooltipDistance: 10,
        pinchZoomX: true,
      })
  );

  // Create axes
  // https://www.amcharts.com/docs/v5/charts/xy-chart/axes/
  var xAxis = chart.xAxes.push(
      am5xy.DateAxis.new(root, {
        maxDeviation: 0.2,
        baseInterval: {
          timeUnit: "minute",
          count: 1,
        },
        renderer: am5xy.AxisRendererX.new(root, {}),
        tooltip: am5.Tooltip.new(root, {}),
      })
  );

  //   chart
  //     .get("colors")
  //     .set("colors", [
  //       am5.color("#E5BE01"),
  //       am5.color("#641C34"),
  //       am5.color("#EAE6CA"),
  //       am5.color("#20214F"),
  //       am5.color("#316650"),
  //       am5.color("#E1CC4F"),
  //     ]);

  var yAxis = chart.yAxes.push(
      am5xy.ValueAxis.new(root, {
        renderer: am5xy.AxisRendererY.new(root, {}),
      })
  );

  // Add series
  // https://www.amcharts.com/docs/v5/charts/xy-chart/series/
  for (const { name, items } of data) {
    var series = chart.series.push(
        am5xy.LineSeries.new(root, {
          name: name,
          xAxis: xAxis,
          yAxis: yAxis,
          valueYField: key,
          valueXField: "date",
          tooltip: am5.Tooltip.new(root, {
            pointerOrientation: "horizontal",
            labelText: `${name}: {valueY} ${um}`,
          }),
        })
    );

    series.data.setAll(items);
    series.appear();
  }

  // Add cursor
  // https://www.amcharts.com/docs/v5/charts/xy-chart/cursor/
  var cursor = chart.set(
      "cursor",
      am5xy.XYCursor.new(root, {
        behavior: "none",
      })
  );
  cursor.lineY.set("visible", false);

  // Add legend
  // https://www.amcharts.com/docs/v5/charts/xy-chart/legend-xy-series/
  var legend = chart.rightAxesContainer.children.push(
      am5.Legend.new(root, {
        // width: 200,
        // paddingLeft: 15,
        height: am5.percent(100),
      })
  );

  // When legend item container is unhovered, make all series as they are
  legend.itemContainers.template.events.on("pointerout", function (e) {
    var itemContainer = e.target;
    var series = itemContainer.dataItem.dataContext;

    chart.series.each(function (chartSeries) {
      chartSeries.strokes.template.setAll({
        strokeOpacity: 1,
        strokeWidth: 1,
        stroke: chartSeries.get("fill"),
      });
    });
  });

  legend.itemContainers.template.set("width", am5.p100);
  legend.valueLabels.template.setAll({
    width: am5.p100,
    textAlign: "right",
  });

  // It's is important to set legend data after all the events are set on template, otherwise events won't be copied
  legend.data.setAll(chart.series.values);

  // Make stuff animate on load
  // https://www.amcharts.com/docs/v5/concepts/animations/
  chart.appear(1000, 100);
}
