function toggle(id, $link) {
    $node = document.getElementById(id);
    
    if (!$node)
    return;
    
    if (!$node.style.display || $node.style.display == 'none') {
    	$node.style.display = 'block';
    	$link.innerHTML = 'Hide source &nequiv;';
    } else {
    	$node.style.display = 'none';
    	$link.innerHTML = 'Show source &equiv;';
    }
}