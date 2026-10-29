start_trial() {
  export TRIAL_START=$(date +%s.%N)
  echo "Trial started."
}

end_trial() {
  local direction=$1
  local trial=$2
  local result=$3
  if [ -z "$TRIAL_START" ]; then
    echo "ERROR: run start_trial first!"
    return 1
  fi
  echo "$TRIAL_START,$(date +%s.%N),$direction,$trial,$result" >> ~/rma_trial_log.csv
  echo "Logged: $direction trial $trial -> $result"
  unset TRIAL_START
}

new_material() {
  echo "start_time,end_time,direction,trial,result" > ~/rma_trial_log.csv
  rm -f ~/rma_data.csv
  echo "Fresh trial log and data file ready. Now run: ~/start_rma.sh"
}

finish_material() {
  local name=$1
  mv ~/rma_data.csv ~/rma_data_${name}.csv
  mv ~/rma_trial_log.csv ~/rma_trial_log_${name}.csv
  echo "Saved as rma_data_${name}.csv and rma_trial_log_${name}.csv"
}
