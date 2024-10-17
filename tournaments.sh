#!/bin/bash

for ns in {1..10}; do
    for ew in {1..10}; do
        python Guess-my-Hand.py --nsStrategy $ns --nsGuesses $ns --ewStrategy $ew --ewGuesses $ew --nSims 1000 --seed 1 --log true
    done
done