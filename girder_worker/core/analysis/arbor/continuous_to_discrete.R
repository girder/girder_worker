newtable <- table
newtable[,paste("discrete", column, thresh, sep="_")] <- ifelse(table[,column] > thresh, 1, 0)
