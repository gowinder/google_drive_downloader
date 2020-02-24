var interval = 10000;

function insert_worker_row(tablet_id, item) {
  last_log = "";
  if (item.progress.logs.length > 0)
    last_log = item.progress.logs[item.progress.logs.length - 1];
  markup = `<tr id='${item.id}'>
            <td>
                <a href="/action?type=cancel&id=${
                  item.id
                }" class="btn btn-secondary" role="button">cancel</a>
            </td>
            <td id="worker_id">${item.id}</td>
            <td>${item.title}</td>
            <td>${item.status}</td>
            <td>${item.error}</td>
            <td>${item.title}</td>
            <td>
                <div>${item.progress.total_progress_desc}</div>
                <div class="progress">
                    <div class="progress-bar" style="width:${item.progress
                      .total_progress * 100}%"></div>
                </div>
            </td>
            <td>
              <div>${item.progress.current_progress_desc}</div>
                <div class="progress">
                    <div class="progress-bar" style="width:${item.progress
                      .current_progress * 100}%"></div>
                </div>
            </td>
            <td>${item.last_update}</td>
            <td>${last_log}</td>
        </tr>`;
  tableBody = $("#" + tablet_id);
  tableBody.append(markup).fadeIn();
}

function update_worker_row(row, item) {
  if (row.children()[8].innerHTML == item.last_update) return;
  else {
    row.children()[3].innerHTML = item.status;
    row.children()[4].innerHTML = item.error;
    row.children()[5].innerHTML = item.current_file;
    row.children()[6].childNodes[1].innerHTML =
      item.progress.total_progress_desc;
    row
      .find("td:eq(6)")
      .find(".progress-bar")
      .css("width", item.progress.total_progress * 100 + "%");
    row.children()[7].childNodes[1].innerHTML =
      item.progress.current_progress_desc;
    row
      .find("td:eq(7)")
      .find(".progress-bar")
      .css("width", item.progress.current_progress * 100 + "%");
    row.children()[8].innerHTML = item.last_update;
  }
}

function check_worker(table_id, item) {
  sel = "#" + item.id;
  row = $(sel);
  if ($(sel).length == 0) {
    insert_worker_row(table_id, item);
  } else {
    if (
      $(sel)
        .parent()
        .parent()
        .attr("id") != table_id
    ) {
      $(sel).prependTo($("#" + table_id));
    }
    update_worker_row($(sel), item);
  }
}

function update_worker(item) {
  if (item.status == 4) {
    // done
    check_worker("tb_done", item);
  } else if (item.status == 5) {
    check_worker("tb_canelled", item);
  } else {
    check_worker("tb_working", item);
  }
}

function reload() {
  $.ajax({
    url: "/worker_list",
    success: function(data, status) {
      console.log("data is ", data, " status: ", status);
      var obj = JSON.parse(data);
      console.log("obj type=", typeof obj);
      $.each(obj, function(idx, item) {
        console.log("idx=", idx, ",item=", item.id);
        update_worker(item);
      });
      // for (id in data) {
      //     console.log('id=', id, ' type=', typeof id)
      //     worker = data[id]
      //     console.log('worker=', worker, ' type=', typeof worker)
      //     // console.log('worker=', obj[id])
      // }
      setTimeout(reload, (timeout = interval));
      console.log("reload.ajex.success ");
    },
    timeout: 1000, //in milliseconds
    error: function() {
      setTimeout(reload, (timeout = interval));
      console.log("reload.ajex.error ");
    }
  });
}

// $(document).ready(
//     reload()
// );

$.when($.ready).then(function() {
  console.log("ready...");
  setTimeout(reload, 2000);
});
