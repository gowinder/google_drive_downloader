
$(document).ready(
    function () {
        setInterval(
            function () {
                console.log('refresh...');
                $.get("/worker_list", function (data, status) {
                    console.log('data is ', data);
                }
                );
            },
            5000
        );
    }
);