
var interval = 10000

var intervalId = 0


function insert_worker_row(item) {
    markup = "<tr><td>This is row "
        + lineNo + "</td></tr>";
    tableBody = $("table tbody");
    tableBody.append(markup);
}

function update_worker_row(row, item) {
    if (row.children()[8].text() == item.last_update)
        return
    else {
        row.children()[3].text(item.status)
        row.children()[4].text(item.error)
        row.children()[5].text(item.current_file)
        row.children()[6].text(item.total_progress)
        row.children()[7].text(item.current_progress)
    }
}

function check_worker(table_id, item) {
    row = document.getElementById(item.id);
    sel = '#' + item.id
    if ($(sel).length == 0) {
        insert_worker_row(item)
    } else {
        if ($(sel).parent().id != table_id) {
            $(sel).prependTo($('#' + table_id))
        }
        update_worker_row($(sel), item)
    }
}

function update_worker(item) {
    if (item.status == 4) { // done
        check_worker('tb_done', item)
    }
    else if (item.status == 5) {
        check_worker('tb_canelled', item)
    }
    else {
        check_worker('tb_working', item)
    }
}

function reload() {
    // console.log('reload..., intervalId=', intervalId);
    // if (intervalId != 0) {
    //     clearInterval(intervalId);
    // }

    $.ajax({
        url: "/worker_list",
        success: function (data, status) {
            console.log('data is ', data, ' status: ', status);
            var obj = JSON.parse(data);
            console.log('obj type=', typeof obj)
            $.each(obj, function (idx, item) {
                console.log('idx=', idx, ',item=', item.id)
                update_worker(item)
            });
            // for (id in data) {
            //     console.log('id=', id, ' type=', typeof id)
            //     worker = data[id]
            //     console.log('worker=', worker, ' type=', typeof worker)
            //     // console.log('worker=', obj[id])
            // }
            setTimeout(reload, timeout = interval);
            console.log('reload.ajex.success intervalId=', intervalId);
        },
        timeout: 1000, //in milliseconds
        error: function () {
            setTimeout(reload, timeout = interval);
            console.log('reload.ajex.error intervalId=', intervalId);
        }
    });


};

// $(document).ready(
//     reload()
// );

$.when($.ready).then(function () {
    console.log('ready...')
    setTimeout(reload, 2000);
    console.log('read intervalId=', intervalId)
});