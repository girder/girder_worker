output<-read.csv(text=input, check.names=FALSE)

# Don't allow empty strings for column names
names(output) <- gsub("^$", "X", names(output))

# If first column contains unique values, set the row names
if (anyDuplicated(output[,1]) == 0) {
    row.names(output)<-output[,1]
}