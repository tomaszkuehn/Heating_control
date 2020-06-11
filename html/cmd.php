<?php

#error_reporting(E_ALL);
$data = $_POST['data'];
#$data = "1 2 3";
$f = fopen('/tmp/heating_pipe', 'w+');
fwrite($f, $data);
fclose($f);
print "ok $data";
?>
